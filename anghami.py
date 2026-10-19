# pylint: disable=C0114
import io
import json
import logging
import re
import time
from dataclasses import dataclass

import aiohttp

from database import database
from constants import (
    ANGHAMI_QUALITY,
    RAPIDAPI_HOST,
    RAPIDAPI_KEY,
    SEARCH_CACHE_TTL,
    SEARCH_MAX_RESULTS,
    TRACK_CACHE_TTL,
    URL_CACHE_CAP,
)

log = logging.getLogger(__name__)

_COVER_CACHE: dict[int, bytes] = {}
_COVER_CACHE_CAP = 128


class AnghamiError(Exception):
    pass


class AnghamiNotFound(AnghamiError):
    pass


class AnghamiRateLimited(AnghamiError):
    pass


class AnghamiUnavailable(AnghamiError):
    pass


@dataclass(slots=True)
class Track:
    id: str
    title: str
    artist: str
    album: str
    duration: float
    cover_id: int
    bitrates: str

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'duration': self.duration,
            'cover_id': self.cover_id,
            'bitrates': self.bitrates,
        }


def track_from_dict(data: dict) -> Track:
    return Track(
        id=str(data.get('id', '')),
        title=data.get('title') or 'بدون عنوان',
        artist=data.get('artist') or 'غير معروف',
        album=data.get('album') or '',
        duration=float(data.get('duration') or 0),
        cover_id=int(data.get('coverArt') or data.get('AlbumArt') or 0),
        bitrates=data.get('bitrates') or '',
    )


async def _download_cover(cover_id: int) -> bytes | None:
    try:
        async with aiohttp.request(
            'GET',
            f'https://artwork.anghcdn.co/?id={cover_id}&size=640',
            headers={'Accept': 'image/jpeg'},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status != 200:
                return None
            return await response.read()
    except aiohttp.ClientError:
        return None
    except TimeoutError:
        return None


async def cover_file(cover_id: int) -> io.BytesIO | None:
    if not cover_id:
        return None
    data = _COVER_CACHE.get(cover_id)
    if data is None:
        data = await _download_cover(cover_id)
        if not data:
            return None
        if len(_COVER_CACHE) >= _COVER_CACHE_CAP:
            _COVER_CACHE.pop(next(iter(_COVER_CACHE)))
        _COVER_CACHE[cover_id] = data
    buffer = io.BytesIO(data)
    buffer.name = f'{cover_id}.jpg'
    return buffer


def format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds or 0), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{secs:02d}'
    return f'{minutes}:{secs:02d}'


_SONG_LINK = re.compile(r'(?:play\.)?anghami\.com/song/(\d+)')


def song_id_from_link(text: str) -> str | None:
    match = _SONG_LINK.search(text)
    if match is None:
        return None
    return match.group(1)


async def _get(path: str, params: dict | None = None) -> dict | None:
    try:
        async with aiohttp.request(
            'GET',
            f'https://{RAPIDAPI_HOST}{path}',
            params=params,
            headers={'x-rapidapi-key': RAPIDAPI_KEY, 'x-rapidapi-host': RAPIDAPI_HOST},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            if response.status == 429:
                raise AnghamiRateLimited('anghami rate limit reached')
            if response.status == 404:
                return None
            if response.status != 200:
                raise AnghamiUnavailable(f'anghami returned status {response.status}')
            return await response.json(content_type=None)
    except aiohttp.ClientError as exc:
        raise AnghamiUnavailable('anghami request failed') from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise AnghamiUnavailable('anghami request timed out or returned bad data') from exc


async def search(query: str, limit: int = 1) -> list[Track]:
    clean_query = query.strip()
    if not clean_query:
        return []
    log.info('anghami search - query %s', clean_query)
    raw = await database.get(f'anghami:search:{clean_query.lower()}')
    if raw is not None:
        try:
            cached = json.loads(raw)
        except json.JSONDecodeError:
            await database.delete(f'anghami:search:{clean_query.lower()}')
            cached = None
        if cached is not None:
            return [track_from_dict(item) for item in cached][:limit]

    tracks = [
        track_from_dict(item)
        for item in (
            (await _get('/search', {'filter_type': 'top', 'q': clean_query})) or {}
        ).get('results') or []
        if item.get('id')
    ]
    await database.set(
        f'anghami:search:{clean_query.lower()}',
        json.dumps([track.to_dict() for track in tracks]),
        ex=SEARCH_CACHE_TTL,
    )
    return tracks[: max(1, min(limit, SEARCH_MAX_RESULTS))]


async def track_info(song_id: str) -> Track:
    log.info('anghami track info - id %s', song_id)
    raw = await database.get(f'anghami:track:{song_id}')
    if raw is not None:
        try:
            return Track(**json.loads(raw))
        except json.JSONDecodeError:
            await database.delete(f'anghami:track:{song_id}')

    payload = await _get(f'/songs/{song_id}')
    if not payload:
        raise AnghamiNotFound(f'song {song_id} not found')
    track = track_from_dict(payload)
    await database.set(f'anghami:track:{song_id}', json.dumps(track.to_dict()), ex=TRACK_CACHE_TTL)
    return track


def _url_ttl(url: str) -> int:
    if 'token=' not in url:
        return URL_CACHE_CAP
    token = url.split('token=', 1)[1].split('_', 1)[0]
    if not token.isdigit():
        return URL_CACHE_CAP
    return max(30, min(URL_CACHE_CAP, int(token) - int(time.time()) - 30))


async def stream_url(song_id: str, quality: str = ANGHAMI_QUALITY) -> str:
    log.info('anghami stream url - id %s quality %s', song_id, quality)
    cached = await database.get(f'anghami:url:{song_id}:{quality}')
    if cached:
        return cached

    payload = await _get(f'/songs/{song_id}/url', {'quality': quality})
    if not payload or not payload.get('url'):
        raise AnghamiNotFound(f'no stream url for song {song_id}')
    url = payload['url']
    await database.set(f'anghami:url:{song_id}:{quality}', url, ex=_url_ttl(url))
    return url
