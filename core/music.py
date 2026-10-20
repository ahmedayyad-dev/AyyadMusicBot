# pylint: disable=C0114
import logging
import secrets
from contextlib import suppress

from pyrogram.enums import ChatType
from pyrogram.errors import RPCError
from pyrogram.types import InputRichBlockParagraph, InputRichMessage, Message, ReplyParameters

from core import anghami, helper, nowplaying, player
from core.config import DOWNLOAD_TOKEN_TTL, QUEUE_LIMIT, bot, database
from languages import get_language, text

log = logging.getLogger(__name__)


def _rich(lang: str, key: str, **kwargs) -> InputRichMessage:
    return InputRichMessage(
        blocks=[InputRichBlockParagraph(text=text(lang, key, **kwargs))],
        is_rtl=(lang == 'ar'),
    )


async def _send_status(
    chat_id: int, key: str, reply_to: int | None = None, lang: str | None = None
) -> Message:
    return await bot.send_rich_message(
        chat_id,
        _rich(lang if lang is not None else await get_language(chat_id), key),
        reply_parameters=ReplyParameters(message_id=reply_to) if reply_to else None,
    )


async def _set_status(message: Message, key: str, lang: str | None = None, **kwargs) -> None:
    with suppress(RPCError):
        await bot.edit_message_text(
            message.chat.id,
            message.id,
            rich_message=_rich(
                lang if lang is not None else await get_language(message.chat.id), key, **kwargs
            ),
        )


async def _clear_status(message: Message) -> None:
    with suppress(RPCError):
        await message.delete()


async def _search(status: Message, query: str, lang: str | None = None) -> anghami.Track | None:
    link_id = anghami.song_id_from_link(query)
    if link_id is None and not query.strip():
        await _set_status(status, 'unknown_song', lang=lang)
        return None
    try:
        if link_id is not None:
            tracks = [await anghami.track_info(link_id)]
        else:
            tracks = await anghami.search(query, limit=1)
    except anghami.AnghamiRateLimited:
        await _set_status(status, 'rate_limited', lang=lang)
        return None
    except anghami.AnghamiNotFound:
        await _set_status(status, 'unknown_song', lang=lang)
        return None
    except anghami.AnghamiError:
        await _set_status(status, 'unavailable', lang=lang)
        return None
    if not tracks:
        await _set_status(status, 'unknown_song', lang=lang)
        return None
    return tracks[0]


async def _play(chat_id: int, stream_url: str, status: Message, lang: str | None = None) -> None:
    await _set_status(status, 'status_playing', lang=lang)
    await helper.play_stream(chat_id, stream_url)


async def start_play(message: Message, query: str, lang: str | None = None) -> None:
    chosen_lang = lang if lang is not None else await get_language(message.chat.id)
    status = await _send_status(message.chat.id, 'status_searching', message.id, chosen_lang)
    track = await _search(status, query, chosen_lang)
    if track is None:
        return
    chat_id = message.chat.id
    async with player.player_manager.lock_for(chat_id):
        playback = player.get_playback(chat_id)
        if playback.is_playing:
            queued, position = playback.enqueue(track, message.from_user.id, QUEUE_LIMIT)
            if not queued:
                await _set_status(status, 'queue_full', chosen_lang, limit=QUEUE_LIMIT)
                return
            await _set_status(
                status, 'added_to_queue', chosen_lang, title=track.title, position=position
            )
            await helper.prepare_next(chat_id)
            return
        item = player.QueueItem(track=track, requested_by=message.from_user.id)
        try:
            await _set_status(status, 'status_loading', chosen_lang)
            await _play(chat_id, await anghami.stream_url(track.id), status, chosen_lang)
            playback.set_current(item)
        except helper.NoHelperAvailable:
            player.close(chat_id)
            await _set_status(status, 'no_helper', chosen_lang)
            return
        except helper.CallUnavailable:
            player.close(chat_id)
            await _set_status(status, 'call_unavailable', chosen_lang)
            return
        except helper.HelperJoinError as exc:
            player.close(chat_id)
            await _set_status(status, 'helper_join_failed', chosen_lang, reason=str(exc))
            return
        except anghami.AnghamiError:
            player.close(chat_id)
            await _set_status(status, 'unavailable', chosen_lang)
            return
        except helper.PlayStreamError:
            player.close(chat_id)
            await anghami.invalidate_url(track.id)
            await _set_status(status, 'load_failed', chosen_lang)
            return
        await nowplaying.send(chat_id, item, status)
        await helper.prepare_next(chat_id)


async def skip(message: Message, lang: str | None = None) -> None:
    chat_id = message.chat.id
    chosen_lang = lang if lang is not None else await get_language(chat_id)
    async with player.player_manager.lock_for(chat_id):
        if not player.is_playing(chat_id):
            await message.reply(text(chosen_lang, 'queue_empty'))
            return
        item = await helper.play_next(chat_id)
        if item is None:
            await message.reply(text(chosen_lang, 'skip_ended'))
        else:
            await message.reply(
                text(chosen_lang, 'skip_done_next', track=f'{item.track.title} - {item.track.artist}')
            )


async def pause(message: Message, lang: str | None = None) -> None:
    chat_id = message.chat.id
    chosen_lang = lang if lang is not None else await get_language(chat_id)
    async with player.player_manager.lock_for(chat_id):
        if not player.is_playing(chat_id):
            await message.reply(text(chosen_lang, 'queue_empty'))
            return
        await helper.pause_call(chat_id)
        player.set_paused(chat_id, True)
        await message.reply(text(chosen_lang, 'pause_done'))
        await nowplaying.refresh(chat_id)


async def resume(message: Message, lang: str | None = None) -> None:
    chat_id = message.chat.id
    chosen_lang = lang if lang is not None else await get_language(chat_id)
    async with player.player_manager.lock_for(chat_id):
        if not player.is_playing(chat_id):
            await message.reply(text(chosen_lang, 'queue_empty'))
            return
        await helper.resume_call(chat_id)
        player.set_paused(chat_id, False)
        await message.reply(text(chosen_lang, 'resume_done'))
        await nowplaying.refresh(chat_id)


async def stop(message: Message, lang: str | None = None) -> None:
    chat_id = message.chat.id
    async with player.player_manager.lock_for(chat_id):
        await helper.leave_call(chat_id, leave_chat=False)
        await nowplaying.clear(chat_id)
        player.close(chat_id)
        await message.reply(
            text(lang if lang is not None else await get_language(chat_id), 'stop_done')
        )


async def show_queue(message: Message, lang: str | None = None) -> None:
    current, upcoming = player.queue_snapshot(message.chat.id)
    await nowplaying.send_queue(message.chat.id, current, upcoming, 0, lang)


async def _upload(status: Message, chat_id: int, stream_url: str, track: anghami.Track) -> None:
    await _set_status(status, 'status_loading')
    try:
        await bot.edit_message_text(
            chat_id, status.id, rich_message=await nowplaying.build_audio(track, stream_url)
        )
    except RPCError as exc:
        log.warning('failed editing audio into status in chat %s: %s', chat_id, exc)
        await bot.send_audio(chat_id, stream_url, caption=nowplaying.track_line(track))
        await _clear_status(status)


async def _deliver(status: Message, chat_id: int, track: anghami.Track) -> None:
    await _set_status(status, 'status_loading')
    try:
        await _upload(status, chat_id, await anghami.stream_url(track.id), track)
    except anghami.AnghamiError:
        await _set_status(status, 'load_failed')


async def handle_download(message: Message, query: str, lang: str | None = None) -> None:
    status = await _send_status(message.chat.id, 'status_searching', message.id, lang)
    track = await _search(status, query, lang)
    if track is None:
        return
    if message.chat.type == ChatType.PRIVATE:
        await _deliver(status, message.chat.id, track)
        return
    token = secrets.token_urlsafe(8)
    await database.set(f'{bot.me.id}:dl:{token}', track.id, ex=DOWNLOAD_TOKEN_TTL)
    await nowplaying.send_download_prompt(
        status, track, f'https://t.me/{bot.me.username}?start=dl_{token}'
    )


async def open_download(chat_id: int, token: str) -> None:
    status = await _send_status(chat_id, 'status_searching')
    async with database.pipeline() as pipe:
        pipe.get(f'{bot.me.id}:dl:{token}')
        pipe.delete(f'{bot.me.id}:dl:{token}')
        track_id, _ = await pipe.execute()
    if track_id is None:
        await _set_status(status, 'download_expired')
        return
    try:
        await _deliver(status, chat_id, await anghami.track_info(track_id))
    except anghami.AnghamiError:
        await _set_status(status, 'load_failed')
