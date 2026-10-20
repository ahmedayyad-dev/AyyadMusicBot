# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import access
import helper
import permissions
import player
from bot import bot
from database import database
from languages import text


async def panel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    async with database.pipeline() as pipe:
        for command in access.COMMANDS:
            pipe.get(f'{bot.me.id}:group:{chat_id}:perm:{command}')
        pipe.get(f'{bot.me.id}:group:{chat_id}:anghami_queue')
        results = await pipe.execute()
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{text(None, f'command_{command}')} "
                    f"{text(None, 'scope_all' if current == access.SCOPE_ALL else 'scope_admins')}"
                ),
                callback_data=(
                    f"setp:{command}:"
                    f"{access.SCOPE_ADMINS if current == access.SCOPE_ALL else access.SCOPE_ALL}"
                ),
                style=(
                    ButtonStyle.SUCCESS
                    if current == access.SCOPE_ALL
                    else ButtonStyle.DANGER
                ),
            )
        ]
        for command, current in zip(access.COMMANDS, results[:-1])
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text=text(None, 'setting_anghami_queue'),
                callback_data='toggle:anghami_queue',
                style=ButtonStyle.SUCCESS if results[-1] != 'off' else ButtonStyle.DANGER,
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


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


@Client.on_callback_query(filters.regex(r'^toggle:anghami_queue$'))
async def toggle_anghami_queue(client: Client, query: CallbackQuery) -> None:
    chat_id = query.message.chat.id
    if not await permissions.has_perm(chat_id, query.from_user.id, 'can_manage_video_chats'):
        await query.answer(text(None, 'settings_admin_only'), show_alert=True)
        return
    enabled = await helper.anghami_queue_enabled(chat_id)
    await helper.set_anghami_queue(chat_id, not enabled)
    if enabled:
        player.clear_autoplay(chat_id)
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
