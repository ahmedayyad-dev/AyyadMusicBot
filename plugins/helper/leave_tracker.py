# pylint: disable=C0114
import logging
from contextlib import suppress

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import ChatMemberUpdated

from core.helper import chat_owner

log = logging.getLogger(__name__)


async def _helper_left_filter(flt, _, update: ChatMemberUpdated) -> bool:
    new = update.new_chat_member
    return bool(
        new
        and new.user
        and new.user.is_self
        and new.status in {ChatMemberStatus.BANNED, ChatMemberStatus.LEFT}
    )


helper_left = filters.create(_helper_left_filter, 'HelperLeft')


@Client.on_chat_member_updated(helper_left & (filters.group | filters.channel))
async def handle_helper_leave(client: Client, update: ChatMemberUpdated) -> None:
    log.info('helper left chat %s', update.chat.id)
    with suppress(ValueError):
        client.chats.remove(update.chat.id)
    chat_owner.pop(update.chat.id, None)
