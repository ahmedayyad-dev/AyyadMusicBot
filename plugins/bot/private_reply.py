# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.types import Message

from core import music
from core.config import bot
from languages import get_language
from plugins.bot.commands_menu import build_private_menu, fetch_stats

HANDLED_TOKENS = {'تشغيل', 'شغل', 'تحميل', '/play', '/download', 'ijro', 'yuklash'}


@Client.on_message(filters.private & filters.text, group=2)
async def private_handler(client: Client, message: Message) -> None:
    if message.from_user is None:
        return
    parts = message.text.split(maxsplit=1)
    first = parts[0] if parts else ''
    lang = await get_language(message.chat.id)
    if first.startswith('/start'):
        payload = parts[1] if len(parts) > 1 else ''
        if payload.startswith('dl_'):
            await music.open_download(message.chat.id, payload[3:])
            return
        await bot.send_rich_message(message.chat.id, build_private_menu(lang, await fetch_stats()))
        return
    if first.startswith('/') or first in HANDLED_TOKENS:
        return
    await bot.send_rich_message(message.chat.id, build_private_menu(lang, await fetch_stats()))
