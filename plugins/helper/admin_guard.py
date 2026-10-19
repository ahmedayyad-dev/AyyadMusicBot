# pylint: disable=C0114
import logging

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import ChatMemberUpdated

from helper import mirror_bot_privileges

log = logging.getLogger(__name__)


async def _helper_demoted_filter(flt, _, update: ChatMemberUpdated) -> bool:
    new = update.new_chat_member
    if not new.user or not new.user.is_self:
        return False
    if new.status not in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.RESTRICTED,
    }:
        return False
    privileges = new.privileges
    return not (privileges and privileges.can_manage_video_chats and privileges.can_restrict_members)


helper_demoted = filters.create(_helper_demoted_filter, 'HelperDemoted')


@Client.on_chat_member_updated(helper_demoted & (filters.group | filters.channel))
async def handle_grant_back(client: Client, update: ChatMemberUpdated) -> None:
    log.warning('helper lost privileges - restoring rights for chat %s', update.chat.id)
    await mirror_bot_privileges(update.chat.id, client.me.id)
