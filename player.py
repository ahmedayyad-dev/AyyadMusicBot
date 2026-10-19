# pylint: disable=C0114
from collections import deque
from dataclasses import dataclass, field

from anghami import Track


@dataclass(slots=True)
class QueueItem:
    track: Track
    requested_by: int


@dataclass(slots=True)
class ChatPlayback:
    queue: deque[QueueItem] = field(default_factory=deque)
    current: QueueItem | None = None
    paused: bool = False
    message_id: int | None = None
    helper_idx: int | None = None


playbacks: dict[int, ChatPlayback] = {}


def get_playback(chat_id: int) -> ChatPlayback:
    playback = playbacks.get(chat_id)
    if playback is None:
        playback = ChatPlayback()
        playbacks[chat_id] = playback
    return playback


def is_playing(chat_id: int) -> bool:
    playback = playbacks.get(chat_id)
    if playback is None:
        return False
    return playback.current is not None


def enqueue(chat_id: int, track: Track, requested_by: int, limit: int) -> tuple[bool, int]:
    playback = get_playback(chat_id)
    if len(playback.queue) >= limit:
        return False, len(playback.queue)
    playback.queue.append(QueueItem(track=track, requested_by=requested_by))
    return True, len(playback.queue)


def set_current(chat_id: int, item: QueueItem | None) -> None:
    playback = get_playback(chat_id)
    playback.current = item
    playback.paused = False


def advance(chat_id: int) -> QueueItem | None:
    playback = playbacks.get(chat_id)
    if playback is None:
        return None
    if playback.queue:
        playback.current = playback.queue.popleft()
    else:
        playback.current = None
    playback.paused = False
    return playback.current


def set_message(chat_id: int, message_id: int | None) -> None:
    get_playback(chat_id).message_id = message_id


def set_helper(chat_id: int, helper_idx: int | None) -> None:
    get_playback(chat_id).helper_idx = helper_idx


def set_paused(chat_id: int, paused: bool) -> None:
    get_playback(chat_id).paused = paused


def close(chat_id: int) -> None:
    playbacks.pop(chat_id, None)


def queue_snapshot(chat_id: int) -> tuple[QueueItem | None, list[QueueItem]]:
    playback = playbacks.get(chat_id)
    if playback is None:
        return None, []
    return playback.current, list(playback.queue)
