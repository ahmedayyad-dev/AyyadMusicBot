# pylint: disable=C0114
import json

from pyrogram.types import CallbackQuery, Message

from database import database
from bot import bot
from constants import DEV_ADMINS
from languages import text

COMMANDS = ('play', 'download', 'queue', 'skip', 'pause', 'resume', 'stop')
SCOPE_ALL = 'all'
SCOPE_ADMINS = 'admins'


async def set_command_scope(chat_id: int, command: str, scope: str) -> None:
    if scope not in (SCOPE_ALL, SCOPE_ADMINS):
        raise ValueError(f'unknown scope {scope}')
    await database.set(f'{bot.me.id}:group:{chat_id}:perm:{command}', scope)


def _target(update: Message | CallbackQuery) -> tuple[int, int]:
    if isinstance(update, CallbackQuery):
        return update.message.chat.id, update.from_user.id
    return update.chat.id, update.from_user.id


async def _deny(update: Message | CallbackQuery) -> None:
    if isinstance(update, CallbackQuery):
        await update.answer(text(None, 'no_perm'), show_alert=True)
        return
    await update.reply(text(None, 'no_perm'))


async def ensure_access(update: Message | CallbackQuery, command: str) -> bool:
    chat_id, user_id = _target(update)
    if user_id in DEV_ADMINS.values():
        return True
    async with database.pipeline() as pipe:
        pipe.get(f'{bot.me.id}:group:{chat_id}:perm:{command}')
        pipe.hget(f'{bot.me.id}:group:{chat_id}:admins', str(user_id))
        scope, raw = await pipe.execute()
    if scope != SCOPE_ADMINS:
        return True
    try:
        if raw and json.loads(raw).get('can_manage_video_chats'):
            return True
    except json.JSONDecodeError:
        pass
    await _deny(update)
    return False
