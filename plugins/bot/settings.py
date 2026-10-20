# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from core import helper, player
from core.config import bot, database
from core.permissions import (
    COMMANDS,
    SCOPE_ADMINS,
    SCOPE_ALL,
    refresh_admins,
    require_admin,
    set_command_scope,
)
from languages import DEFAULT_LANGUAGE, LANGUAGES, set_language, text


async def panel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    async with database.pipeline() as pipe:
        for command in COMMANDS:
            pipe.get(f'{bot.me.id}:group:{chat_id}:perm:{command}')
        pipe.get(f'{bot.me.id}:group:{chat_id}:anghami_queue')
        pipe.get(f'{bot.me.id}:group:{chat_id}:lang')
        results = await pipe.execute()
    raw_lang = results[-1]
    chat_lang = raw_lang if raw_lang in LANGUAGES else DEFAULT_LANGUAGE
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{text(chat_lang, f'action_{command}')} "
                    f"{text(chat_lang, 'scope_all' if current == SCOPE_ALL else 'scope_admins')}"
                ),
                callback_data=(
                    f"setp:{command}:"
                    f"{SCOPE_ADMINS if current == SCOPE_ALL else SCOPE_ALL}"
                ),
                style=(
                    ButtonStyle.SUCCESS
                    if current == SCOPE_ALL
                    else ButtonStyle.DANGER
                ),
            )
        ]
        for command, current in zip(COMMANDS, results[: len(COMMANDS)])
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text=(
                    f"{text(chat_lang, 'setting_anghami_queue')}: "
                    f"{text(chat_lang, 'anghami_queue_on' if results[-2] != 'off' else 'anghami_queue_off')}"
                ),
                callback_data='toggle:anghami_queue',
                style=ButtonStyle.SUCCESS if results[-2] != 'off' else ButtonStyle.DANGER,
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=f"{text(chat_lang, 'setting_group_lang')}: {LANGUAGES[chat_lang]['lang_name']}",
                callback_data='toggle:group_lang',
                style=ButtonStyle.PRIMARY,
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


@Client.on_message(
    filters.regex(r'^(اعدادات|الاعدادات|/settings|sozlamalar)$') & filters.group
)
@require_admin()
async def settings_command(client: Client, message: Message, lang: str) -> None:
    await message.reply(
        text(lang, 'settings_body'), reply_markup=await panel_keyboard(message.chat.id)
    )


@Client.on_callback_query(filters.regex(r'^setp'))
@require_admin()
async def set_perm(client: Client, query: CallbackQuery, lang: str) -> None:
    parts = query.data.split(':')
    if len(parts) < 3:
        await query.answer()
        return
    _, command, scope = parts
    if command not in COMMANDS:
        await query.answer()
        return
    chat_id = query.message.chat.id
    await set_command_scope(chat_id, command, scope)
    await query.answer(text(lang, 'settings_saved'))
    await query.message.edit_text(
        text(lang, 'settings_body'), reply_markup=await panel_keyboard(chat_id)
    )


@Client.on_callback_query(filters.regex(r'^toggle:anghami_queue$'))
@require_admin()
async def toggle_anghami_queue(client: Client, query: CallbackQuery, lang: str) -> None:
    chat_id = query.message.chat.id
    enabled = await helper.anghami_queue_enabled(chat_id)
    await helper.set_anghami_queue(chat_id, not enabled)
    if enabled:
        player.clear_autoplay(chat_id)
    await query.answer(text(lang, 'settings_saved'))
    await query.message.edit_text(
        text(lang, 'settings_body'), reply_markup=await panel_keyboard(chat_id)
    )


@Client.on_callback_query(filters.regex(r'^toggle:group_lang$'))
@require_admin()
async def toggle_group_lang(client: Client, query: CallbackQuery, lang: str) -> None:
    chat_id = query.message.chat.id
    order = ('ar', 'en', 'uz')
    next_lang = order[(order.index(lang) + 1) % len(order)]
    await set_language(chat_id, next_lang)
    await query.answer(text(next_lang, 'settings_saved'))
    await query.message.edit_text(
        text(next_lang, 'settings_body'), reply_markup=await panel_keyboard(chat_id)
    )


@Client.on_message(filters.regex(r'^(تحديث|/reload|/refresh|yangilash)$') & filters.group)
@require_admin()
async def reload_admins_command(client: Client, message: Message, lang: str) -> None:
    try:
        await refresh_admins(message.chat.id)
    except RPCError:
        await message.reply(text(lang, 'admins_refresh_failed'))
        return
    await message.reply(text(lang, 'admins_refreshed'))
