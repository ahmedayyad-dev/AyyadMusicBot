# pylint: disable=C0114
import json
import logging
from enum import StrEnum
from functools import wraps

from pyrogram import Client
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus
from pyrogram.types import CallbackQuery, Message

from core.config import DEV_ADMINS, bot, database
from languages import get_language, text

log = logging.getLogger(__name__)


class CommandScope(StrEnum):
    ALL = 'all'
    ADMINS = 'admins'


SCOPE_ALL = CommandScope.ALL
SCOPE_ADMINS = CommandScope.ADMINS

COMMANDS = ('play', 'download', 'queue', 'skip', 'pause', 'resume', 'stop')

_PRIVILEGE_ATTRS = (
    'can_manage_chat',
    'can_delete_messages',
    'can_manage_video_chats',
    'can_restrict_members',
    'can_promote_members',
    'can_change_info',
    'can_invite_users',
    'can_post_stories',
    'can_edit_stories',
    'can_delete_stories',
    'can_post_messages',
    'can_edit_messages',
    'can_pin_messages',
    'can_manage_topics',
    'can_manage_direct_messages',
    'can_manage_tags',
    'can_send_welcome_messages',
)


async def set_command_scope(chat_id: int, command: str, scope: str | CommandScope) -> None:
    if scope not in (CommandScope.ALL, CommandScope.ADMINS):
        raise ValueError(f'unknown scope {scope}')
    await database.set(f'{bot.me.id}:group:{chat_id}:perm:{command}', str(scope))


def _target(update: Message | CallbackQuery) -> tuple[int, int]:
    if isinstance(update, CallbackQuery):
        return update.message.chat.id, update.from_user.id
    return update.chat.id, update.from_user.id


async def _deny(update: Message | CallbackQuery) -> None:
    chat_id, user_id = _target(update)
    lang = await get_language(chat_id, user_id)
    if isinstance(update, CallbackQuery):
        await update.answer(text(lang, 'no_perm'), show_alert=True)
        return
    await update.reply(text(lang, 'no_perm'))


async def ensure_access(update: Message | CallbackQuery, command: str) -> bool:
    chat_id, user_id = _target(update)
    if user_id in DEV_ADMINS.values():
        return True
    async with database.pipeline() as pipe:
        pipe.get(f'{bot.me.id}:group:{chat_id}:perm:{command}')
        pipe.hget(f'{bot.me.id}:group:{chat_id}:admins', str(user_id))
        scope, raw = await pipe.execute()
    if scope != CommandScope.ADMINS:
        return True
    try:
        if raw and json.loads(raw).get('can_manage_video_chats'):
            return True
    except json.JSONDecodeError:
        pass
    await _deny(update)
    return False


async def refresh_admins(chat_id: int) -> None:
    privileges: dict[int, dict] = {}
    async for member in bot.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
        if not member.user:
            continue
        if member.status != ChatMemberStatus.OWNER and member.privileges:
            privileges[member.user.id] = {
                _attr: getattr(member.privileges, _attr, False)
                for _attr in _PRIVILEGE_ATTRS
            }
        else:
            privileges[member.user.id] = {_attr: True for _attr in _PRIVILEGE_ATTRS}
    mapping = {str(user_id): json.dumps(flags) for user_id, flags in privileges.items()}
    async with database.pipeline() as pipe:
        if mapping:
            pipe.hset(f'{bot.me.id}:group:{chat_id}:admins', mapping=mapping)
        pipe.delete(f'{bot.me.id}:group:{chat_id}:admin')


async def _has_perm(chat_id: int, user_id: int, permission: str) -> bool:
    if user_id in DEV_ADMINS.values():
        return True
    raw = await database.hget(f'{bot.me.id}:group:{chat_id}:admins', str(user_id))
    if raw is None:
        return False
    try:
        return bool(json.loads(raw).get(permission))
    except json.JSONDecodeError:
        return False


def require_access(command: str):
    """Enforce command access permission, auto-denying unauthorized updates and injecting lang."""

    def decorator(func):
        @wraps(func)
        async def wrapper(_client: Client, update: Message | CallbackQuery, *args, **kwargs):
            if not await ensure_access(update, command):
                return
            return await func(
                _client,
                update,
                await get_language(
                    update.message.chat.id if isinstance(update, CallbackQuery) else update.chat.id,
                    update.from_user.id if update.from_user else None,
                ),
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


def require_admin(permission: str = 'can_manage_video_chats'):
    """Enforce admin permission, auto-denying non-admins and injecting lang."""

    def decorator(func):
        @wraps(func)
        async def wrapper(_client: Client, update: Message | CallbackQuery, *args, **kwargs):
            chat_id = (
                update.message.chat.id
                if isinstance(update, CallbackQuery)
                else update.chat.id
            )
            user_id = update.from_user.id if update.from_user else None
            if not user_id or not await _has_perm(chat_id, user_id, permission):
                lang = await get_language(chat_id, user_id)
                if isinstance(update, CallbackQuery):
                    await update.answer(
                        text(lang, 'settings_admin_only'),
                        show_alert=True,
                    )
                else:
                    await update.reply(
                        text(lang, 'settings_admin_only')
                    )
                return
            return await func(
                _client, update, await get_language(chat_id, user_id), *args, **kwargs
            )

        return wrapper

    return decorator
