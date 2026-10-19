# pylint: disable=C0114
from pyrogram.types import (
    InputRichBlockButtons,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichMessage,
    RichMessageButton,
)

from constants import SOURCE_URL
from languages import text


def _commands_list() -> InputRichBlockList:
    return InputRichBlockList(
        items=[
            InputRichBlockListItem(blocks=[InputRichBlockParagraph(text=text(None, key))])
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


def build_welcome() -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=text(None, 'welcome_title'), size=2),
            InputRichBlockParagraph(text=text(None, 'welcome_body')),
            InputRichBlockParagraph(text=text(None, 'welcome_usage')),
            _commands_list(),
        ],
        is_rtl=True,
    )


def build_private_menu() -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=text(None, 'welcome_title'), size=2),
            InputRichBlockParagraph(text=text(None, 'private_body')),
            _commands_list(),
            InputRichBlockButtons(
                buttons=[
                    RichMessageButton(text=text(None, 'source_button'), url=SOURCE_URL)
                ]
            ),
        ],
        is_rtl=True,
    )
