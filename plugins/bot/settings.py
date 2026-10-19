# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import access
import permissions
from bot import bot
from database import database
from languages import text


async def panel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    async with database.pipeline() as pipe:
        for command in access.COMMANDS:
            pipe.get(f'{bot.me.id}:group:{chat_id}:perm:{command}')
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text(None, f'command_{command}'),
                        callback_data='setp',
                        style=ButtonStyle.DEFAULT,
                    ),
                    InlineKeyboardButton(
                        text=(
                            f"[{text(None, 'scope_all')}]"
                            if current == access.SCOPE_ALL
                            else text(None, 'scope_all')
                        ),
                        callback_data=f'setp:{command}:all',
                        style=ButtonStyle.PRIMARY
                        if current == access.SCOPE_ALL
                        else ButtonStyle.DEFAULT,
                    ),
                    InlineKeyboardButton(
                        text=(
                            f"[{text(None, 'scope_admins')}]"
                            if current == access.SCOPE_ADMINS
                            else text(None, 'scope_admins')
                        ),
                        callback_data=f'setp:{command}:admins',
                        style=ButtonStyle.PRIMARY
                        if current == access.SCOPE_ADMINS
                        else ButtonStyle.DEFAULT,
                    ),
                ]
                for command, current in zip(access.COMMANDS, await pipe.execute())
            ]
        )


@Client.on_message(filters.regex(r'^(اعدادات|/settings)$') & filters.group & filters.text)
async def settings_command(client: Client, message: Message) -> None:
    if not await permissions.has_perm(
        message.chat.id, message.from_user.id, 'can_manage_video_chats'
    ):
        await message.reply(text(None, 'settings_admin_only'))
        return
    await message.reply(
        text(None, 'settings_body'), reply_markup=await panel_keyboard(message.chat.id)
    )


@Client.on_callback_query(filters.regex(r'^setp'))
async def set_perm(client: Client, query: CallbackQuery) -> None:
    chat_id = query.message.chat.id
    if not await permissions.has_perm(chat_id, query.from_user.id, 'can_manage_video_chats'):
        await query.answer(text(None, 'settings_admin_only'), show_alert=True)
        return
    parts = query.data.split(':')
    if len(parts) < 3:
        await query.answer()
        return
    _, command, scope = parts
    if command not in access.COMMANDS:
        await query.answer()
        return
    await access.set_command_scope(chat_id, command, scope)
    await query.answer(text(None, 'settings_saved'))
    await query.message.edit_text(
        text(None, 'settings_body'), reply_markup=await panel_keyboard(chat_id)
    )


@Client.on_message(filters.regex(r'^(تحديث|/reload|/refresh)$') & filters.group & filters.text)
async def reload_admins_command(client: Client, message: Message) -> None:
    try:
        await permissions.refresh_admins(message.chat.id)
    except RPCError:
        await message.reply(text(None, 'admins_refresh_failed'))
        return
    await message.reply(text(None, 'admins_refreshed'))
