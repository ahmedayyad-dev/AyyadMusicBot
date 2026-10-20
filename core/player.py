# pylint: disable=C0114,R0902
from asyncio import Lock
from collections import deque
from dataclasses import dataclass, field

from core.anghami import Track


@dataclass(slots=True)
class QueueItem:
    track: Track
    requested_by: int
    autoplay: bool = False


@dataclass(slots=True)
class ChatPlayback:
    queue: deque[QueueItem] = field(default_factory=deque)
    autoplay: deque[Track] = field(default_factory=deque)
    autoplay_seed: str | None = None
    current: QueueItem | None = None
    paused: bool = False
    message_id: int | None = None

    @property
    def is_playing(self) -> bool:
        return self.current is not None

    def enqueue(self, track: Track, requested_by: int, limit: int) -> tuple[bool, int]:
        if len(self.queue) >= limit:
            return False, len(self.queue)
        self.autoplay.clear()
        self.autoplay_seed = None
        self.queue.append(QueueItem(track=track, requested_by=requested_by))
        return True, len(self.queue)

    def set_current(self, item: QueueItem | None) -> None:
        if item is None or item.autoplay or (
            self.autoplay_seed is not None and item.track.id != self.autoplay_seed
        ):
            self.autoplay.clear()
            self.autoplay_seed = None
        self.current = item
        self.paused = False

    def advance(self) -> QueueItem | None:
        if self.queue:
            self.current = self.queue.popleft()
            if self.autoplay_seed is not None and self.current.track.id != self.autoplay_seed:
                self.autoplay.clear()
                self.autoplay_seed = None
        else:
            self.current = None
        self.paused = False
        return self.current

    def set_autoplay(self, tracks: list[Track], seed_id: str | None = None) -> None:
        if seed_id is None:
            seed_id = self.last_manual_seed()
        self.autoplay.clear()
        self.autoplay_seed = seed_id
        seen = {seed_id} if seed_id else set()
        for track in tracks:
            if track.id in seen:
                continue
            seen.add(track.id)
            self.autoplay.append(track)

    def last_manual_seed(self) -> str | None:
        if self.queue:
            return self.queue[-1].track.id
        if self.current is not None and not self.current.autoplay:
            return self.current.track.id
        return None

    def clear_autoplay(self) -> None:
        self.autoplay.clear()
        self.autoplay_seed = None

    def next_autoplay(self) -> QueueItem | None:
        if not self.autoplay:
            return None
        item = QueueItem(track=self.autoplay.popleft(), requested_by=0, autoplay=True)
        self.current = item
        self.paused = False
        return item

    def peek_next(self) -> Track | None:
        if self.queue:
            return self.queue[0].track
        if self.autoplay:
            return self.autoplay[0]
        return None

    def queue_snapshot(self) -> tuple[QueueItem | None, list[QueueItem]]:
        upcoming = list(self.queue)
        upcoming.extend(
            QueueItem(track=track, requested_by=0, autoplay=True) for track in self.autoplay
        )
        return self.current, upcoming


class PlaybackManager:
    __slots__ = ('_locks', '_playbacks')

    def __init__(self) -> None:
        self._playbacks: dict[int, ChatPlayback] = {}
        self._locks: dict[int, Lock] = {}

    def get(self, chat_id: int) -> ChatPlayback:
        playback = self._playbacks.get(chat_id)
        if playback is None:
            playback = ChatPlayback()
            self._playbacks[chat_id] = playback
        return playback

    def lock_for(self, chat_id: int) -> Lock:
        lock = self._locks.get(chat_id)
        if lock is None:
            lock = Lock()
            self._locks[chat_id] = lock
        return lock

    def is_playing(self, chat_id: int) -> bool:
        playback = self._playbacks.get(chat_id)
        return playback is not None and playback.is_playing

    def close(self, chat_id: int) -> None:
        self._playbacks.pop(chat_id, None)
        self._locks.pop(chat_id, None)

    @property
    def playbacks(self) -> dict[int, ChatPlayback]:
        return self._playbacks


player_manager = PlaybackManager()

get_playback = player_manager.get
is_playing = player_manager.is_playing
close = player_manager.close
playbacks = player_manager.playbacks


def advance(chat_id: int) -> QueueItem | None:
    return player_manager.get(chat_id).advance()


def set_autoplay(chat_id: int, tracks: list[Track], seed_id: str | None = None) -> None:
    player_manager.get(chat_id).set_autoplay(tracks, seed_id)


def last_manual_seed(chat_id: int) -> str | None:
    return player_manager.get(chat_id).last_manual_seed()


def clear_autoplay(chat_id: int) -> None:
    player_manager.get(chat_id).clear_autoplay()


def next_autoplay(chat_id: int) -> QueueItem | None:
    return player_manager.get(chat_id).next_autoplay()


def peek_next(chat_id: int) -> Track | None:
    return player_manager.get(chat_id).peek_next()


def set_message(chat_id: int, message_id: int | None) -> None:
    player_manager.get(chat_id).message_id = message_id


def set_paused(chat_id: int, paused: bool) -> None:
    player_manager.get(chat_id).paused = paused


def queue_snapshot(chat_id: int) -> tuple[QueueItem | None, list[QueueItem]]:
    return player_manager.get(chat_id).queue_snapshot()
