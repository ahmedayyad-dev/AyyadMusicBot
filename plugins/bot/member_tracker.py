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


def _is_admin(member) -> bool:
    if not member or not getattr(member, 'user', None):
        return False
    return member.status in (
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    )


_KNOWN_CHATS: set[int] = set()


@Client.on_message(group=-1)
async def member_handler(client: Client, update: Message) -> None:
    chat_id = update.chat.id
    if chat_id in _KNOWN_CHATS:
        return
    _KNOWN_CHATS.add(chat_id)
    if chat_id < 0:
        if update.chat.type == ChatType.CHANNEL:
            if await database.sadd(f'{bot.me.id}:channel', chat_id):
                log.info('bot added to channel - %s', chat_id)
        elif await database.sadd(f'{bot.me.id}:group', chat_id):
            log.info('bot joined group - %s', chat_id)
            await refresh_admins(chat_id)
            await bot.send_rich_message(chat_id, build_welcome())
    else:
        await database.sadd(f'{bot.me.id}:private', chat_id)


@Client.on_chat_member_updated(filters.group | filters.channel)
async def track_admin_changes(client: Client, update: ChatMemberUpdated) -> None:
    old = update.old_chat_member
    new = update.new_chat_member
    if not old or not new:
        return
    if _is_admin(old) != _is_admin(new):
        try:
            await refresh_admins(update.chat.id)
        except Exception:
            log.exception('failed to refresh admins after member update in %s', update.chat.id)
        return
    if _is_admin(new):
        if getattr(old, 'privileges', None) != getattr(new, 'privileges', None):
            try:
                await refresh_admins(update.chat.id)
            except Exception:
                log.exception('failed to refresh admins after privilege update in %s', update.chat.id)


@Client.on_chat_member_updated(bot_left_group & (filters.group | filters.channel))
async def leave_handler(client: Client, update: ChatMemberUpdated) -> None:
    kind = 'channel' if update.chat.type == ChatType.CHANNEL else 'group'
    log.info('bot left %s - chat %s', kind, update.chat.id)
    async with database.pipeline() as pipe:
        pipe.srem(f'{bot.me.id}:{kind}', update.chat.id)
        pipe.delete(f'{bot.me.id}:group:{update.chat.id}:admins')
        await pipe.execute()
    _KNOWN_CHATS.discard(update.chat.id)
    await leave_call(update.chat.id, leave_chat=True)
    await bot.leave_chat(update.chat.id)
