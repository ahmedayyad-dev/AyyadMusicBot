# pylint: disable=C0114
import logging

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import ChatMemberUpdated, Message

from core.config import bot, database
from core.helper import leave_call
from core.permissions import refresh_admins
from plugins.bot.commands_menu import build_welcome

log = logging.getLogger(__name__)


async def _bot_left_filter(flt, _, update: ChatMemberUpdated) -> bool:
    old = update.old_chat_member
    new = update.new_chat_member
    return bool(
        old
        and old.user
        and old.user.is_self
        and (not new or new.status != ChatMemberStatus.ADMINISTRATOR)
    )


bot_left_group = filters.create(_bot_left_filter, 'BotLeftGroup')


@Client.on_message(group=-1)
async def member_handler(client: Client, update: Message) -> None:
    if update.chat.id < 0:
        if update.chat.type == ChatType.CHANNEL:
            if await database.sadd(f'{bot.me.id}:channel', update.chat.id):
                log.info('bot added to channel - %s', update.chat.id)
        elif await database.sadd(f'{bot.me.id}:group', update.chat.id):
            log.info('bot joined group - %s', update.chat.id)
            await refresh_admins(update.chat.id)
            await bot.send_rich_message(update.chat.id, build_welcome())
    else:
        await database.sadd(f'{bot.me.id}:private', update.chat.id)


@Client.on_chat_member_updated(bot_left_group & (filters.group | filters.channel))
async def leave_handler(client: Client, update: ChatMemberUpdated) -> None:
    kind = 'channel' if update.chat.type == ChatType.CHANNEL else 'group'
    log.info('bot left %s - chat %s', kind, update.chat.id)
    async with database.pipeline() as pipe:
        pipe.srem(f'{bot.me.id}:{kind}', update.chat.id)
        pipe.delete(f'{bot.me.id}:group:{update.chat.id}:admins')
        await pipe.execute()
    await leave_call(update.chat.id, leave_chat=True)
    await bot.leave_chat(update.chat.id)
