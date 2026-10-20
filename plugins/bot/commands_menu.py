# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.types import (
    CallbackQuery,
    InputRichBlockButtons,
    InputRichBlockDivider,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
    RichBlockTableCell,
    RichMessageButton,
)

from core import helper
from core.config import SOURCE_URL, bot, database
from languages import LANGUAGES, get_language, set_language, text


def _commands_list(lang: str = 'ar') -> InputRichBlockList:
    return InputRichBlockList(
        items=[
            InputRichBlockListItem(blocks=[InputRichBlockParagraph(text=text(lang, key))])
            for key in (
                'help_play',
                'help_download',
                'help_queue',
                'help_skip',
                'help_pause',
                'help_resume',
                'help_stop',
                'help_reload',
                'help_settings',
            )
        ]
    )


async def fetch_stats() -> tuple[int, int, int, int]:
    async with database.pipeline() as pipe:
        pipe.scard(f'{bot.me.id}:private')
        pipe.scard(f'{bot.me.id}:group')
        pipe.scard(f'{bot.me.id}:channel')
        counts = await pipe.execute()
    return counts[0], counts[1], counts[2], len(helper.chat_owner)


def build_welcome(lang: str = 'ar') -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=text(lang, 'welcome_title'), size=2),
            InputRichBlockParagraph(text=text(lang, 'welcome_body')),
            InputRichBlockParagraph(text=text(lang, 'welcome_usage')),
            _commands_list(lang),
        ],
        is_rtl=(lang == 'ar'),
    )


def build_private_menu(lang: str, stats: tuple[int, int, int, int]) -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=text(lang, 'welcome_title'), size=2),
            InputRichBlockParagraph(text=text(lang, 'private_body')),
            _commands_list(lang),
            InputRichBlockDivider(),
            InputRichBlockSectionHeading(text=text(lang, 'stats_title'), size=2),
            InputRichBlockTable(
                cells=[
                    [
                        RichBlockTableCell(text=text(lang, 'stats_private'), is_header=True),
                        RichBlockTableCell(text=text(lang, 'stats_groups'), is_header=True),
                    ],
                    [
                        RichBlockTableCell(text=str(stats[0])),
                        RichBlockTableCell(text=str(stats[1])),
                    ],
                    [
                        RichBlockTableCell(text=text(lang, 'stats_channels'), is_header=True),
                        RichBlockTableCell(text=text(lang, 'stats_calls'), is_header=True),
                    ],
                    [
                        RichBlockTableCell(text=str(stats[2])),
                        RichBlockTableCell(text=str(stats[3])),
                    ],
                ],
                is_bordered=True,
                is_striped=True,
            ),
            InputRichBlockButtons(
                buttons=[
                    RichMessageButton(
                        text=text(lang, 'action_language'),
                        callback_data='lang:menu',
                        style=ButtonStyle.PRIMARY,
                    ),
                    RichMessageButton(
                        text=text(lang, 'source_button'),
                        url=SOURCE_URL,
                    ),
                ]
            ),
        ],
        is_rtl=(lang == 'ar'),
    )


def build_language_picker(lang: str = 'ar') -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=text(lang, 'choose_language'), size=2),
            InputRichBlockButtons(
                buttons=[
                    RichMessageButton(
                        text='العربية' if lang != 'ar' else '✓ العربية',
                        callback_data='lang:set:ar',
                        style=ButtonStyle.SUCCESS if lang == 'ar' else ButtonStyle.PRIMARY,
                    ),
                    RichMessageButton(
                        text='English' if lang != 'en' else '✓ English',
                        callback_data='lang:set:en',
                        style=ButtonStyle.SUCCESS if lang == 'en' else ButtonStyle.PRIMARY,
                    ),
                    RichMessageButton(
                        text="O'zbekcha" if lang != 'uz' else "✓ O'zbekcha",
                        callback_data='lang:set:uz',
                        style=ButtonStyle.SUCCESS if lang == 'uz' else ButtonStyle.PRIMARY,
                    ),
                    RichMessageButton(
                        text=text(lang, 'action_back'),
                        callback_data='lang:back',
                        style=ButtonStyle.DANGER,
                    ),
                ]
            ),
        ],
        is_rtl=(lang == 'ar'),
    )


@Client.on_callback_query(filters.regex(r'^lang:'))
async def language_callback(client: Client, query: CallbackQuery) -> None:
    user_id = query.from_user.id
    current_lang = await get_language(user_id)
    data = query.data
    if data == 'lang:menu':
        await bot.edit_message_text(
            query.message.chat.id,
            query.message.id,
            rich_message=build_language_picker(current_lang),
        )
        await query.answer()
        return
    if data == 'lang:back':
        await bot.edit_message_text(
            query.message.chat.id,
            query.message.id,
            rich_message=build_private_menu(current_lang, await fetch_stats()),
        )
        await query.answer()
        return
    if data.startswith('lang:set:'):
        target_lang = data.split(':', 2)[2]
        if target_lang in LANGUAGES:
            await set_language(user_id, target_lang)
            await query.answer(
                text(target_lang, 'language_chosen', lang=LANGUAGES[target_lang]['lang_name'])
            )
            await bot.edit_message_text(
                query.message.chat.id,
                query.message.id,
                rich_message=build_private_menu(target_lang, await fetch_stats()),
            )
            return
    await query.answer()
