# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.types import Message

import access
import music_service
from languages import text


@Client.on_message(filters.regex(r'^(تشغيل|شغل|/play)(\s|$)') & filters.text & filters.group)
async def play_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'play'):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        await music_service.start_play(message, parts[1])
        return
    await message.reply(text(None, 'play_usage'))


@Client.on_message(filters.regex(r'^(تشغيل|شغل|/play)(\s|$)') & filters.text & filters.private)
async def play_private_handler(client: Client, message: Message) -> None:
    await message.reply(text(None, 'play_in_group_only'))


@Client.on_message(
    filters.regex(r'^https?://(?:play\.)?anghami\.com/song/\d+') & filters.text & filters.group
)
async def play_link_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'play'):
        return
    await music_service.start_play(message, message.text)


@Client.on_message(filters.regex(r'^(تحميل|/download)(\s|$)') & filters.text & ~filters.via_bot)
async def download_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'download'):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        await music_service.handle_download(message, parts[1])
        return
    await message.reply(text(None, 'download_usage'))


@Client.on_message(filters.regex(r'^(الطابور|/queue)$') & filters.text & filters.group)
async def queue_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'queue'):
        return
    await music_service.show_queue(message)


@Client.on_message(filters.regex(r'^(تخطي|/skip)$') & filters.text & filters.group)
async def skip_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'skip'):
        return
    await music_service.skip(message)


@Client.on_message(filters.regex(r'^(ايقاف|/pause)$') & filters.text & filters.group)
async def pause_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'pause'):
        return
    await music_service.pause(message)


@Client.on_message(filters.regex(r'^(استئناف|/resume)$') & filters.text & filters.group)
async def resume_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'resume'):
        return
    await music_service.resume(message)


@Client.on_message(filters.regex(r'^(انهاء|/end|/stop)$') & filters.text & filters.group)
async def stop_handler(client: Client, message: Message) -> None:
    if not await access.ensure_access(message, 'stop'):
        return
    await music_service.stop(message)
