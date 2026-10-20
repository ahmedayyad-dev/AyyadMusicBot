# pylint: disable=C0114
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

from core.config import bot
from languages import get_language, text

log = logging.getLogger(__name__)


@Client.on_message(filters.private & filters.incoming)
async def helper_private_info(client: Client, message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot or message.from_user.is_self:
        return
    log.info('helper private message - from %s', message.from_user.id)
    await message.reply(
        text(await get_language(message.chat.id), 'helper_private_desc', bot_username=bot.me.username)
    )
