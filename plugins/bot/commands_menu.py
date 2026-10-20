# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.types import (
    CallbackQuery,
    InputRichBlockButtons,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichMessage,
    RichMessageButton,
)

from core.config import SOURCE_URL, bot
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


def build_private_menu(lang: str = 'ar') -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=text(lang, 'welcome_title'), size=2),
            InputRichBlockParagraph(text=text(lang, 'private_body')),
            _commands_list(lang),
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
            rich_message=build_private_menu(current_lang),
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
                rich_message=build_private_menu(target_lang),
            )
            return
    await query.answer()
