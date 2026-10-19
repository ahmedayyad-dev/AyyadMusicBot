# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.types import Message

import music_service
from bot import bot
from plugins.bot.commands_menu import build_private_menu

HANDLED_TOKENS = {'تشغيل', 'شغل', 'تحميل'}


@Client.on_message(filters.private & filters.text, group=2)
async def private_handler(client: Client, message: Message) -> None:
    if message.from_user is None:
        return
    parts = message.text.split(maxsplit=1)
    first = parts[0] if parts else ''
    if first.startswith('/start'):
        payload = parts[1] if len(parts) > 1 else ''
        if payload.startswith('dl_'):
            await music_service.open_download(message.chat.id, payload[3:])
            return
        await bot.send_rich_message(message.chat.id, build_private_menu())
        return
    if first.startswith('/') or first in HANDLED_TOKENS:
        return
    await bot.send_rich_message(message.chat.id, build_private_menu())
