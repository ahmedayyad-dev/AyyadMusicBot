# pylint: disable=C0114
import logging
from contextlib import suppress

from pyrogram.enums import ButtonStyle
from pyrogram.errors import RPCError
from pyrogram.types import (
    InputMediaAudio,
    InputMediaPhoto,
    InputRichBlockAudio,
    InputRichBlockButtons,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichBlockSectionHeading,
    InputRichMessage,
    Message,
    RichMessageButton,
)

from core import anghami, player
from core.config import QUEUE_PAGE_SIZE, bot
from languages import get_language, text

log = logging.getLogger(__name__)


def track_line(track: anghami.Track) -> str:
    return f'{track.title} - {track.artist}'


def _buttons(chat_id: int, lang: str = 'ar') -> InputRichBlockButtons:
    playback = player.playbacks.get(chat_id)
    items = [
        RichMessageButton(
            text=text(lang, 'action_skip'), callback_data='mq:skip', style=ButtonStyle.PRIMARY
        )
    ]
    if playback is not None and playback.paused:
        items.append(
            RichMessageButton(
                text=text(lang, 'action_resume'),
                callback_data='mq:resume',
                style=ButtonStyle.SUCCESS,
            )
        )
    else:
        items.append(
            RichMessageButton(
                text=text(lang, 'action_pause'),
                callback_data='mq:pause',
                style=ButtonStyle.PRIMARY,
            )
        )
    items.append(
        RichMessageButton(
            text=text(lang, 'action_stop'), callback_data='mq:stop', style=ButtonStyle.DANGER
        )
    )
    return InputRichBlockButtons(buttons=items)


async def _photo(cover_id: int) -> InputRichBlockPhoto | None:
    file = await anghami.cover_file(cover_id)
    if file is None:
        return None
    return InputRichBlockPhoto(photo=InputMediaPhoto(media=file))


async def _build_now_playing(
    chat_id: int, item: player.QueueItem, lang: str | None = None
) -> InputRichMessage:
    chosen_lang = lang if lang is not None else await get_language(chat_id)
    track = item.track
    blocks = []
    photo = await _photo(track.cover_id)
    if photo is not None:
        blocks.append(photo)
    blocks.append(InputRichBlockSectionHeading(text=text(chosen_lang, 'now_playing_title'), size=1))
    blocks.append(InputRichBlockParagraph(text=track_line(track)))
    blocks.append(
        InputRichBlockParagraph(
            text=text(chosen_lang, 'duration_line', duration=anghami.format_duration(track.duration))
        )
    )
    blocks.append(_buttons(chat_id, chosen_lang))
    return InputRichMessage(blocks=blocks, is_rtl=(chosen_lang == 'ar'))


async def build_audio(
    track: anghami.Track, stream_url: str, lang: str = 'ar'
) -> InputRichMessage:
    blocks = []
    photo = await _photo(track.cover_id)
    if photo is not None:
        blocks.append(photo)
    blocks.append(
        InputRichBlockAudio(
            audio=InputMediaAudio(
                media=stream_url,
                duration=int(track.duration),
                performer=track.artist,
                title=track.title,
            )
        )
    )
    blocks.append(InputRichBlockParagraph(text=track_line(track)))
    return InputRichMessage(blocks=blocks, is_rtl=(lang == 'ar'))


async def send(chat_id: int, item: player.QueueItem, status: Message | None = None) -> None:
    if status is not None:
        try:
            await bot.edit_message_text(
                chat_id, status.id, rich_message=await _build_now_playing(chat_id, item)
            )
            player.set_message(chat_id, status.id)
            return
        except RPCError as exc:
            log.warning('failed editing status into now playing in chat %s: %s', chat_id, exc)
            with suppress(RPCError):
                await status.delete()
    await clear(chat_id)
    sent = await bot.send_rich_message(chat_id, await _build_now_playing(chat_id, item))
    if sent is not None:
        player.set_message(chat_id, sent.id)


async def refresh(chat_id: int) -> None:
    playback = player.playbacks.get(chat_id)
    if playback is None or playback.current is None or playback.message_id is None:
        return
    try:
        await bot.edit_message_text(
            chat_id,
            playback.message_id,
            rich_message=await _build_now_playing(chat_id, playback.current),
        )
    except RPCError as exc:
        log.warning('failed refreshing now playing in chat %s: %s', chat_id, exc)


async def clear(chat_id: int) -> None:
    playback = player.playbacks.get(chat_id)
    if playback is None or playback.message_id is None:
        return
    try:
        await bot.delete_messages(chat_id, playback.message_id)
    except RPCError as exc:
        log.warning('failed clearing now playing in chat %s: %s', chat_id, exc)
    playback.message_id = None


def _build_queue(
    current: player.QueueItem | None,
    upcoming: list[player.QueueItem],
    page: int = 0,
    lang: str = 'ar',
) -> InputRichMessage:
    blocks = []
    pages = max(1, (len(upcoming) + QUEUE_PAGE_SIZE - 1) // QUEUE_PAGE_SIZE)
    current_page = max(0, min(page, pages - 1))
    start = current_page * QUEUE_PAGE_SIZE
    if current is None and not upcoming:
        blocks.append(InputRichBlockParagraph(text=text(lang, 'queue_empty')))
    else:
        blocks.append(InputRichBlockSectionHeading(text=text(lang, 'queue_title'), size=1))
        if upcoming:
            blocks.append(
                InputRichBlockParagraph(text=text(lang, 'queue_count', count=len(upcoming)))
            )
        if current is not None:
            blocks.append(InputRichBlockSectionHeading(text=text(lang, 'queue_now'), size=2))
            blocks.append(InputRichBlockParagraph(text=track_line(current.track)))
            blocks.append(
                InputRichBlockParagraph(
                    text=text(
                        lang,
                        'queue_source_anghami' if current.autoplay else 'queue_source_user',
                    )
                )
            )
        shown_sources = set()
        for position, item in enumerate(
            upcoming[start:start + QUEUE_PAGE_SIZE], start=start + 1
        ):
            if item.autoplay not in shown_sources:
                blocks.append(
                    InputRichBlockSectionHeading(
                        text=text(
                            lang,
                            'queue_anghami_title' if item.autoplay else 'queue_next',
                        ),
                        size=3,
                    )
                )
                if item.autoplay:
                    blocks.append(
                        InputRichBlockParagraph(text=text(lang, 'queue_anghami_note'))
                    )
                shown_sources.add(item.autoplay)
            blocks.append(InputRichBlockParagraph(text=f'{position}. {track_line(item.track)}'))
        if pages > 1:
            blocks.append(
                InputRichBlockParagraph(
                    text=text(lang, 'queue_page', page=current_page + 1, pages=pages)
                )
            )
        buttons = []
        if current_page > 0:
            buttons.append(
                RichMessageButton(
                    text=text(lang, 'action_back'),
                    callback_data=f'mq:queue:{current_page - 1}',
                    style=ButtonStyle.PRIMARY,
                )
            )
        if current_page < pages - 1:
            buttons.append(
                RichMessageButton(
                    text=text(lang, 'action_next'),
                    callback_data=f'mq:queue:{current_page + 1}',
                    style=ButtonStyle.PRIMARY,
                )
            )
        if buttons:
            blocks.append(InputRichBlockButtons(buttons=buttons))
    return InputRichMessage(blocks=blocks, is_rtl=(lang == 'ar'))


async def send_queue(
    chat_id: int,
    current: player.QueueItem | None,
    upcoming: list[player.QueueItem],
    page: int = 0,
    lang: str | None = None,
) -> None:
    await bot.send_rich_message(
        chat_id,
        _build_queue(
            current,
            upcoming,
            page,
            lang if lang is not None else await get_language(chat_id),
        ),
    )


async def edit_queue(
    chat_id: int,
    message_id: int,
    current: player.QueueItem | None,
    upcoming: list[player.QueueItem],
    page: int,
) -> None:
    try:
        await bot.edit_message_text(
            chat_id,
            message_id,
            rich_message=_build_queue(current, upcoming, page, await get_language(chat_id)),
        )
    except RPCError as exc:
        log.warning('failed editing queue in chat %s: %s', chat_id, exc)


async def send_download_prompt(status: Message, track: anghami.Track, link: str) -> None:
    lang = await get_language(status.chat.id)
    blocks = []
    photo = await _photo(track.cover_id)
    if photo is not None:
        blocks.append(photo)
    blocks.append(InputRichBlockSectionHeading(text=text(lang, 'download_title'), size=1))
    blocks.append(
        InputRichBlockParagraph(
            text=text(lang, 'download_found', title=track.title, artist=track.artist)
        )
    )
    blocks.append(InputRichBlockParagraph(text=text(lang, 'download_redirect')))
    blocks.append(
        InputRichBlockButtons(
            buttons=[RichMessageButton(text=text(lang, 'download_open_private'), url=link)]
        )
    )
    prompt = InputRichMessage(blocks=blocks, is_rtl=(lang == 'ar'))
    try:
        await bot.edit_message_text(status.chat.id, status.id, rich_message=prompt)
    except RPCError as exc:
        log.warning('failed editing download prompt in chat %s: %s', status.chat.id, exc)
        await bot.send_rich_message(status.chat.id, prompt)
        with suppress(RPCError):
            await status.delete()
