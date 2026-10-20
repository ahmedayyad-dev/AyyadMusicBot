# pylint: disable=C0114
import asyncio
import logging
import time
from contextlib import suppress
from json import JSONDecodeError

from ntgcalls import FFmpegError
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
from pytgcalls.exceptions import NoActiveGroupCall, NoAudioSourceFound, NotInCallError
from pytgcalls.types import ChatUpdate, GroupCallConfig, MediaStream, StreamEnded
from redis.exceptions import RedisError

from core import anghami, nowplaying, player
from core.config import API_HASH, API_ID, HELPER_SESSIONS, bot, database

log = logging.getLogger(__name__)

SWEEP_INTERVAL: int = 60 * 60


class NoHelperAvailable(Exception):
    pass


class HelperJoinError(Exception):
    pass


class CallUnavailable(Exception):
    pass


class PlayStreamError(Exception):
    pass


async def _mark_active(chat_id: int) -> None:
    await database.set(f'{bot.me.id}:chat:{chat_id}:last_active', str(int(time.time())))


async def _recently_active(chat_id: int) -> bool:
    raw_value = await database.get(f'{bot.me.id}:chat:{chat_id}:last_active')
    if raw_value is None:
        return False
    return int(raw_value) > int(time.time()) - 24 * 60 * 60


async def mirror_bot_privileges(chat_id: int, member_id: int) -> None:
    with suppress(RPCError):
        member = await bot.get_chat_member(chat_id, bot.me.id)
        if member.privileges:
            await bot.promote_chat_member(chat_id, member_id, privileges=member.privileges)
            log.info('bot privileges mirrored - chat %s member %s', chat_id, member_id)


class AssistantManager:
    __slots__ = ('chat_owner', 'helpers')

    def __init__(self) -> None:
        self.helpers: list[PyTgCalls] = []
        self.chat_owner: dict[int, int] = {}

    def _pick_helper(self) -> int:
        return min(range(len(self.helpers)), key=lambda _idx: len(self.helpers[_idx].mtproto_client.chats))

    async def _ensure_join(self, call: PyTgCalls, chat_id: int) -> str | None:
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

    async def ensure_assistant(self, chat_id: int) -> int:
        if not self.helpers:
            raise NoHelperAvailable('no helper available')
        idx = self.chat_owner.get(chat_id)
        if idx is None:
            idx = self._pick_helper()
            self.chat_owner[chat_id] = idx
        if chat_id not in self.helpers[idx].mtproto_client.chats:
            join_error = await self._ensure_join(self.helpers[idx], chat_id)
            if join_error:
                raise HelperJoinError(join_error)
        return idx

    async def play_stream(self, chat_id: int, url: str) -> None:
        try:
            await self.helpers[await self.ensure_assistant(chat_id)].play(
                chat_id,
                MediaStream(url, video_flags=MediaStream.Flags.IGNORE),
                config=GroupCallConfig(auto_start=False),
            )
        except NoActiveGroupCall as exc:
            raise CallUnavailable('no active voice chat') from exc
        except (
            FFmpegError,
            ProcessLookupError,
            JSONDecodeError,
            FileNotFoundError,
            TimeoutError,
            NoAudioSourceFound,
            NotInCallError,
        ) as exc:
            log.warning('failed to play stream in chat %s: %s', chat_id, exc)
            raise PlayStreamError(str(exc)) from exc
        await _mark_active(chat_id)

    async def pause_call(self, chat_id: int) -> None:
        idx = self.chat_owner.get(chat_id)
        if idx is None or idx >= len(self.helpers):
            return
        await self.helpers[idx].pause(chat_id)

    async def resume_call(self, chat_id: int) -> None:
        idx = self.chat_owner.get(chat_id)
        if idx is None or idx >= len(self.helpers):
            return
        await self.helpers[idx].resume(chat_id)

    async def leave_call(self, chat_id: int, leave_chat: bool = False) -> None:
        idx = self.chat_owner.get(chat_id)
        if idx is None or idx >= len(self.helpers):
            return
        try:
            await self.helpers[idx].leave_call(chat_id)
        except (NoActiveGroupCall, NotInCallError):
            pass
        if leave_chat:
            with suppress(RPCError):
                await self.helpers[idx].mtproto_client.leave_chat(chat_id)
            with suppress(ValueError):
                self.helpers[idx].mtproto_client.chats.remove(chat_id)
            self.chat_owner.pop(chat_id, None)
        log.info('helper left call - chat %s', chat_id)

    async def anghami_queue_enabled(self, chat_id: int) -> bool:
        return (await database.get(f'{bot.me.id}:group:{chat_id}:anghami_queue')) != 'off'

    async def set_anghami_queue(self, chat_id: int, enabled: bool) -> None:
        await database.set(
            f'{bot.me.id}:group:{chat_id}:anghami_queue', 'on' if enabled else 'off'
        )

    async def _load_autoplay(self, chat_id: int) -> None:
        if not await self.anghami_queue_enabled(chat_id):
            return
        seed_id = player.last_manual_seed(chat_id)
        if seed_id is None:
            return
        playback = player.get_playback(chat_id)
        if playback.autoplay_seed == seed_id and playback.autoplay:
            return
        try:
            tracks = await anghami.queue_tracks(seed_id)
        except (anghami.AnghamiError, RedisError) as exc:
            log.warning('failed loading anghami queue in chat %s: %s', chat_id, exc)
            return
        if not tracks or player.last_manual_seed(chat_id) != seed_id:
            return
        player.set_autoplay(chat_id, tracks, seed_id)

    async def prepare_next(self, chat_id: int) -> None:
        await self._load_autoplay(chat_id)
        next_track = player.peek_next(chat_id)
        if next_track is None:
            return
        try:
            await anghami.stream_url(next_track.id)
        except (anghami.AnghamiError, RedisError) as exc:
            log.warning('failed prefetching next track in chat %s: %s', chat_id, exc)

    async def play_next(self, chat_id: int) -> player.QueueItem | None:
        await self._load_autoplay(chat_id)
        while True:
            item = player.advance(chat_id)
            if item is None:
                item = player.next_autoplay(chat_id)
            if item is None:
                await self.leave_call(chat_id)
                await nowplaying.clear(chat_id)
                player.close(chat_id)
                return None
            try:
                await self.play_stream(chat_id, await anghami.stream_url(item.track.id))
            except (
                anghami.AnghamiError,
                CallUnavailable,
                HelperJoinError,
                NoHelperAvailable,
                PlayStreamError,
            ) as exc:
                log.warning('failed playing next track in chat %s: %s', chat_id, exc)
                continue
            await nowplaying.send(chat_id, item)
            await self.prepare_next(chat_id)
            return item

    async def _leave_idle(self, client: Client, chat_id: int) -> None:
        if chat_id in self.chat_owner:
            await self.leave_call(chat_id, leave_chat=True)
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

    async def _sweep_idle(self, client: Client) -> None:
        for chat_id in list(client.chats):
            try:
                if player.is_playing(chat_id):
                    continue
                if await _recently_active(chat_id):
                    continue
                await self._leave_idle(client, chat_id)
            except (RPCError, RedisError, NotInCallError, NoActiveGroupCall) as exc:
                log.warning('sweep failed for chat %s: %s', chat_id, exc)

    async def _sweep_loop(self, client: Client) -> None:
        await asyncio.sleep(SWEEP_INTERVAL)
        while True:
            await self._sweep_idle(client)
            await asyncio.sleep(SWEEP_INTERVAL)

    async def start_helpers(self) -> None:
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
            call.add_handler(self._on_stream_end, filters.stream_end(StreamEnded.Type.AUDIO))
            call.add_handler(self._on_call_closed, filters.chat_update(ChatUpdate.Status.CLOSED_VOICE_CHAT))
            await call.start()
            async for dialog in client.get_dialogs():
                if dialog.chat.type in {ChatType.SUPERGROUP, ChatType.CHANNEL, ChatType.GROUP}:
                    client.chats.append(dialog.chat.id)
            self.helpers.append(call)
            log.info('helper %s started - member of %s chats', idx, len(client.chats))
            asyncio.create_task(self._sweep_loop(client))

    async def _on_stream_end(self, client: Client, update: StreamEnded) -> None:
        log.info('stream ended - chat %s', update.chat_id)
        await self.play_next(update.chat_id)

    async def _on_call_closed(self, client: Client, update: ChatUpdate) -> None:
        log.info('voice chat closed - chat %s', update.chat_id)
        self.chat_owner.pop(update.chat_id, None)
        player.close(update.chat_id)


assistant_manager = AssistantManager()

chat_owner = assistant_manager.chat_owner
play_stream = assistant_manager.play_stream
pause_call = assistant_manager.pause_call
resume_call = assistant_manager.resume_call
leave_call = assistant_manager.leave_call
anghami_queue_enabled = assistant_manager.anghami_queue_enabled
set_anghami_queue = assistant_manager.set_anghami_queue
prepare_next = assistant_manager.prepare_next
play_next = assistant_manager.play_next
start_helpers = assistant_manager.start_helpers
