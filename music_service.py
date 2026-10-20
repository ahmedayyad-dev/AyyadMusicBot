# pylint: disable=C0114
import logging
import secrets
from contextlib import suppress

from pyrogram.enums import ChatType
from pyrogram.errors import RPCError
from pyrogram.types import InputRichBlockParagraph, InputRichMessage, Message, ReplyParameters

import anghami
from database import database
import helper
import nowplaying
import player
from bot import bot
from constants import DOWNLOAD_TOKEN_TTL, QUEUE_LIMIT
from languages import text

log = logging.getLogger(__name__)


def _rich(key: str, **kwargs) -> InputRichMessage:
    return InputRichMessage(
        blocks=[InputRichBlockParagraph(text=text(None, key, **kwargs))],
        is_rtl=True,
    )


async def _send_status(chat_id: int, key: str, reply_to: int | None = None) -> Message:
    return await bot.send_rich_message(
        chat_id,
        _rich(key),
        reply_parameters=ReplyParameters(message_id=reply_to) if reply_to else None,
    )


async def _set_status(message: Message, key: str, **kwargs) -> None:
    with suppress(RPCError):
        await bot.edit_message_text(
            message.chat.id, message.id, rich_message=_rich(key, **kwargs)
        )


async def _clear_status(message: Message) -> None:
    with suppress(RPCError):
        await message.delete()


async def _search(status: Message, query: str) -> anghami.Track | None:
    link_id = anghami.song_id_from_link(query)
    if link_id is None and not query.strip():
        await _set_status(status, 'unknown_song')
        return None
    try:
        if link_id is not None:
            tracks = [await anghami.track_info(link_id)]
        else:
            tracks = await anghami.search(query, limit=1)
    except anghami.AnghamiRateLimited:
        await _set_status(status, 'rate_limited')
        return None
    except anghami.AnghamiNotFound:
        await _set_status(status, 'unknown_song')
        return None
    except anghami.AnghamiError:
        await _set_status(status, 'unavailable')
        return None
    if not tracks:
        await _set_status(status, 'unknown_song')
        return None
    return tracks[0]


async def _play(chat_id: int, stream_url: str, status: Message) -> None:
    await _set_status(status, 'status_playing')
    await helper.play_stream(chat_id, stream_url)


async def start_play(message: Message, query: str) -> None:
    status = await _send_status(message.chat.id, 'status_searching', message.id)
    track = await _search(status, query)
    if track is None:
        return
    chat_id = message.chat.id
    if player.is_playing(chat_id):
        queued, position = player.enqueue(chat_id, track, message.from_user.id, QUEUE_LIMIT)
        if not queued:
            await _set_status(status, 'queue_full', limit=QUEUE_LIMIT)
            return
        await _set_status(status, 'added_to_queue', title=track.title, position=position)
        await helper.prepare_next(chat_id)
        return
    item = player.QueueItem(track=track, requested_by=message.from_user.id)
    player.set_current(chat_id, item)
    try:
        await _set_status(status, 'status_loading')
        await _play(chat_id, await anghami.stream_url(track.id), status)
    except helper.NoHelperAvailable:
        player.close(chat_id)
        await _set_status(status, 'no_helper')
        return
    except helper.CallUnavailable:
        player.close(chat_id)
        await _set_status(status, 'call_unavailable')
        return
    except helper.HelperJoinError as exc:
        player.close(chat_id)
        await _set_status(status, 'helper_join_failed', reason=str(exc))
        return
    except anghami.AnghamiError:
        player.close(chat_id)
        await _set_status(status, 'unavailable')
        return
    await nowplaying.send(chat_id, item, status)
    await helper.prepare_next(chat_id)


async def skip(message: Message) -> None:
    chat_id = message.chat.id
    if not player.is_playing(chat_id):
        await message.reply(text(None, 'queue_empty'))
        return
    await helper.play_next(chat_id)


async def pause(message: Message) -> None:
    chat_id = message.chat.id
    if not player.is_playing(chat_id):
        await message.reply(text(None, 'queue_empty'))
        return
    await helper.pause_call(chat_id)
    player.set_paused(chat_id, True)
    await message.reply(text(None, 'pause_done'))
    await nowplaying.refresh(chat_id)


async def resume(message: Message) -> None:
    chat_id = message.chat.id
    if not player.is_playing(chat_id):
        await message.reply(text(None, 'queue_empty'))
        return
    await helper.resume_call(chat_id)
    player.set_paused(chat_id, False)
    await message.reply(text(None, 'resume_done'))
    await nowplaying.refresh(chat_id)


async def stop(message: Message) -> None:
    chat_id = message.chat.id
    await helper.leave_call(chat_id, leave_chat=False)
    await nowplaying.clear(chat_id)
    player.close(chat_id)
    await message.reply(text(None, 'stop_done'))


async def show_queue(message: Message) -> None:
    current, upcoming = player.queue_snapshot(message.chat.id)
    await nowplaying.send_queue(message.chat.id, current, upcoming, 0)


async def _upload(status: Message, chat_id: int, stream_url: str, track: anghami.Track) -> None:
    await _set_status(status, 'status_uploading')
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


async def handle_download(message: Message, query: str) -> None:
    status = await _send_status(message.chat.id, 'status_searching', message.id)
    track = await _search(status, query)
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
