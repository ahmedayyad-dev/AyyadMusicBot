# pylint: disable=C0114
import json
import logging

from pyrogram.enums import ChatMembersFilter, ChatMemberStatus

from database import database
from bot import bot
from constants import DEV_ADMINS

log = logging.getLogger(__name__)

PRIVILEGE_ATTRS = (
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


async def refresh_admins(chat_id: int) -> None:
    privileges: dict[int, dict] = {}
    async for member in bot.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
        if not member.user:
            continue
        if member.status != ChatMemberStatus.OWNER and member.privileges:
            privileges[member.user.id] = {
                _attr: getattr(member.privileges, _attr, False)
                for _attr in PRIVILEGE_ATTRS
            }
        else:
            privileges[member.user.id] = {_attr: True for _attr in PRIVILEGE_ATTRS}
    mapping = {str(user_id): json.dumps(flags) for user_id, flags in privileges.items()}
    async with database.pipeline() as pipe:
        if mapping:
            pipe.hset(f'{bot.me.id}:group:{chat_id}:admins', mapping=mapping)
        pipe.delete(f'{bot.me.id}:group:{chat_id}:admin')
        await pipe.execute()
    log.info('admins refreshed for chat %s - count %s', chat_id, len(privileges))


async def has_perm(chat_id: int, user_id: int, permission: str) -> bool:
    if user_id in DEV_ADMINS.values():
        return True
    raw = await database.hget(f'{bot.me.id}:group:{chat_id}:admins', str(user_id))
    if raw is None:
        return False
    try:
        return bool(json.loads(raw).get(permission))
    except json.JSONDecodeError:
        return False
