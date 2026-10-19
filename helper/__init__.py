# pylint: disable=C0114
import asyncio
import logging
import time
from contextlib import suppress

from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import (
    ChannelInvalid,
    ChannelPrivate,
    ChatIdInvalid,
    InviteHashExpired,
    InviteRequestSent,
    RPCError,
    UserAlreadyParticipant,
)
from pyrogram.types import ChatJoinResultRequestSent
from pytgcalls import PyTgCalls, filters
from pytgcalls.exceptions import NoActiveGroupCall, NotInCallError
from pytgcalls.types import ChatUpdate, GroupCallConfig, MediaStream, StreamEnded
from redis.exceptions import RedisError

import anghami
from database import database
import nowplaying
import player
from bot import bot
from constants import API_HASH, API_ID, HELPER_SESSIONS

log = logging.getLogger(__name__)

SWEEP_INTERVAL: int = 60 * 60

helpers: list[PyTgCalls] = []
chat_owner: dict[int, int] = {}


class NoHelperAvailable(Exception):
    pass


class HelperJoinError(Exception):
    pass


class CallUnavailable(Exception):
    pass


async def _mark_active(chat_id: int) -> None:
    await database.set(f'{bot.me.id}:chat:{chat_id}:last_active', str(int(time.time())))


async def _recently_active(chat_id: int) -> bool:
    raw_value = await database.get(f'{bot.me.id}:chat:{chat_id}:last_active')
    if raw_value is None:
        return False
    return int(raw_value) > int(time.time()) - 24 * 60 * 60


def _pick_helper() -> int:
    return min(range(len(helpers)), key=lambda _idx: len(helpers[_idx].mtproto_client.chats))


async def mirror_bot_privileges(chat_id: int, member_id: int) -> None:
    with suppress(RPCError):
        member = await bot.get_chat_member(chat_id, bot.me.id)
        if member.privileges:
            await bot.promote_chat_member(chat_id, member_id, privileges=member.privileges)
            log.info('bot privileges mirrored - chat %s member %s', chat_id, member_id)


async def _ensure_join(call: PyTgCalls, chat_id: int) -> str | None:
    chat = await bot.get_chat(chat_id)
    invite = chat.username or chat.invite_link
    if not invite:
        invite = await bot.export_chat_invite_link(chat.id)
    try:
        if isinstance(
            await call.mtproto_client.join_chat(invite), ChatJoinResultRequestSent
        ):
            await bot.approve_chat_join_request(chat.id, call.mtproto_client.me.id)
    except UserAlreadyParticipant:
        pass
    except InviteRequestSent:
        await bot.approve_chat_join_request(chat.id, call.mtproto_client.me.id)
    except InviteHashExpired:
        return 'invite link expired'
    except (ChannelPrivate, ChannelInvalid, ChatIdInvalid):
        return 'helper cannot join this group'
    if chat.id not in call.mtproto_client.chats:
        call.mtproto_client.chats.append(chat.id)
    await mirror_bot_privileges(chat.id, call.mtproto_client.me.id)
    return None


async def ensure_assistant(chat_id: int) -> int:
    if not helpers:
        raise NoHelperAvailable('no helper available')
    idx = chat_owner.get(chat_id)
    if idx is None:
        idx = _pick_helper()
        chat_owner[chat_id] = idx
    if chat_id not in helpers[idx].mtproto_client.chats:
        join_error = await _ensure_join(helpers[idx], chat_id)
        if join_error:
            raise HelperJoinError(join_error)
    player.set_helper(chat_id, idx)
    return idx


async def play_stream(chat_id: int, url: str) -> None:
    try:
        await helpers[await ensure_assistant(chat_id)].play(
            chat_id, MediaStream(url), config=GroupCallConfig(auto_start=False)
        )
    except NoActiveGroupCall as exc:
        raise CallUnavailable('no active voice chat') from exc
    await _mark_active(chat_id)


async def pause_call(chat_id: int) -> None:
    idx = chat_owner.get(chat_id)
    if idx is None or idx >= len(helpers):
        return
    await helpers[idx].pause(chat_id)


async def resume_call(chat_id: int) -> None:
    idx = chat_owner.get(chat_id)
    if idx is None or idx >= len(helpers):
        return
    await helpers[idx].resume(chat_id)


async def leave_call(chat_id: int, leave_chat: bool = False) -> None:
    idx = chat_owner.get(chat_id)
    if idx is None or idx >= len(helpers):
        return
    try:
        await helpers[idx].leave_call(chat_id)
    except (NoActiveGroupCall, NotInCallError):
        pass
    if leave_chat:
        with suppress(RPCError):
            await helpers[idx].mtproto_client.leave_chat(chat_id)
        with suppress(ValueError):
            helpers[idx].mtproto_client.chats.remove(chat_id)
        chat_owner.pop(chat_id, None)
    log.info('helper left call - chat %s', chat_id)


async def play_next(chat_id: int) -> None:
    while True:
        item = player.advance(chat_id)
        if item is None:
            await leave_call(chat_id)
            await nowplaying.clear(chat_id)
            player.close(chat_id)
            return
        try:
            await play_stream(chat_id, await anghami.stream_url(item.track.id))
        except (anghami.AnghamiError, CallUnavailable, HelperJoinError, NoHelperAvailable) as exc:
            log.warning('failed playing next track in chat %s: %s', chat_id, exc)
            continue
        await nowplaying.send(chat_id, item)
        return


async def _on_stream_end(client: Client, update: StreamEnded) -> None:
    log.info('stream ended - chat %s', update.chat_id)
    await play_next(update.chat_id)


async def _on_call_closed(client: Client, update: ChatUpdate) -> None:
    log.info('voice chat closed - chat %s', update.chat_id)
    chat_owner.pop(update.chat_id, None)
    player.close(update.chat_id)


async def _leave_idle(client: Client, chat_id: int) -> None:
    if chat_id in chat_owner:
        await leave_call(chat_id, leave_chat=True)
        return
    try:
        await client.call.leave_call(chat_id)
    except (NoActiveGroupCall, NotInCallError):
        pass
    try:
        await client.leave_chat(chat_id)
    except RPCError:
        return
    with suppress(ValueError):
        client.chats.remove(chat_id)


async def _sweep_idle(client: Client) -> None:
    for chat_id in list(client.chats):
        try:
            if player.is_playing(chat_id):
                continue
            if await _recently_active(chat_id):
                continue
            await _leave_idle(client, chat_id)
        except (RPCError, RedisError, NotInCallError, NoActiveGroupCall) as exc:
            log.warning('sweep failed for chat %s: %s', chat_id, exc)


async def _sweep_loop(client: Client) -> None:
    await asyncio.sleep(SWEEP_INTERVAL)
    while True:
        await _sweep_idle(client)
        await asyncio.sleep(SWEEP_INTERVAL)


async def start_helpers() -> None:
    for idx, session in enumerate(HELPER_SESSIONS):
        client = Client(
            f'helper:{idx}',
            API_ID,
            API_HASH,
            session_string=session,
            fetch_replies=False,
            fetch_topics=False,
            fetch_stories=False,
            fetch_stickers=False,
            plugins=dict(root='plugins/helper'),
        )
        client.chats = []
        call = PyTgCalls(client)
        client.call = call
        call.add_handler(_on_stream_end, filters.stream_end(StreamEnded.Type.AUDIO))
        call.add_handler(_on_call_closed, filters.chat_update(ChatUpdate.Status.CLOSED_VOICE_CHAT))
        await call.start()
        async for dialog in client.get_dialogs():
            if dialog.chat.type in {ChatType.SUPERGROUP, ChatType.CHANNEL, ChatType.GROUP}:
                client.chats.append(dialog.chat.id)
        helpers.append(call)
        log.info('helper %s started - member of %s chats', idx, len(client.chats))
        asyncio.create_task(_sweep_loop(client))
