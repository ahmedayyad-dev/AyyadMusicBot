# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.types import Message

from core import music
from core.permissions import require_access
from languages import get_language, text


@Client.on_message(filters.regex(r'^(تشغيل|شغل|/play|ijro)(\s|$)') & filters.group)
@require_access('play')
async def play_handler(client: Client, message: Message, lang: str) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        await music.start_play(message, parts[1], lang)
        return
    await message.reply(text(lang, 'play_usage'))


@Client.on_message(filters.regex(r'^(تشغيل|شغل|/play|ijro)(\s|$)') & filters.private)
async def play_private_handler(client: Client, message: Message) -> None:
    await message.reply(text(await get_language(message.chat.id), 'play_in_group_only'))


@Client.on_message(
    filters.regex(r'^https?://(?:play\.)?anghami\.com/song/\d+') & filters.group
)
@require_access('play')
async def play_link_handler(client: Client, message: Message, lang: str) -> None:
    await music.start_play(message, message.text, lang)


@Client.on_message(filters.regex(r'^(تحميل|/download|yuklash)(\s|$)') & ~filters.via_bot)
@require_access('download')
async def download_handler(client: Client, message: Message, lang: str) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        await music.handle_download(message, parts[1], lang)
        return
    await message.reply(text(lang, 'download_usage'))


@Client.on_message(filters.regex(r'^(الطابور|طابور|/queue|navbat)$') & filters.group)
@require_access('queue')
async def queue_handler(client: Client, message: Message, lang: str) -> None:
    await music.show_queue(message, lang)


@Client.on_message(filters.regex(r'^(تخطي|/skip|otkaz|o\'tkaz)$') & filters.group)
@require_access('skip')
async def skip_handler(client: Client, message: Message, lang: str) -> None:
    await music.skip(message, lang)


@Client.on_message(filters.regex(r'^(ايقاف|/pause|pauza)$') & filters.group)
@require_access('pause')
async def pause_handler(client: Client, message: Message, lang: str) -> None:
    await music.pause(message, lang)


@Client.on_message(filters.regex(r'^(استئناف|/resume|davom)$') & filters.group)
@require_access('resume')
async def resume_handler(client: Client, message: Message, lang: str) -> None:
    await music.resume(message, lang)


@Client.on_message(filters.regex(r'^(انهاء|/end|/stop|to\'xtat|toxtat)$') & filters.group)
@require_access('stop')
async def stop_handler(client: Client, message: Message, lang: str) -> None:
    await music.stop(message, lang)
