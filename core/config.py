# pylint: disable=C0114
import os
import tomllib
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from pyrogram import Client
from redis import asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

load_dotenv()


def _load_admins() -> dict[str, int]:
    admins: dict[str, int] = {}
    for entry in os.environ['DEV_ADMINS'].split(','):
        name, _, value = entry.partition(':')
        admins[name.strip()] = int(value)
    return admins


API_ID: Final[int] = int(os.environ['API_ID'])
API_HASH: Final[str] = os.environ['API_HASH']
TOKEN: Final[str] = os.environ['BOT_TOKEN']
HELPER_SESSIONS: Final[list[str]] = os.environ['HELPER_SESSIONS'].split(',')
DEV_ADMINS: Final[dict[str, int]] = _load_admins()
BOT_VERSION: Final[str] = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version']

RAPIDAPI_HOST: Final[str] = 'anghami-music-data-and-stream.p.rapidapi.com'
RAPIDAPI_KEY: Final[str] = os.environ['RAPIDAPI_KEY']

ANGHAMI_QUALITY: Final[str] = '196'
SEARCH_CACHE_TTL: Final[int] = 6 * 60 * 60
TRACK_CACHE_TTL: Final[int] = 24 * 60 * 60
QUEUE_CACHE_TTL: Final[int] = 6 * 60 * 60
URL_CACHE_CAP: Final[int] = 20 * 60
SEARCH_MAX_RESULTS: Final[int] = 10
QUEUE_LIMIT: Final[int] = 50
QUEUE_PAGE_SIZE: Final[int] = 10
DOWNLOAD_TOKEN_TTL: Final[int] = 30 * 60
SOURCE_URL: Final[str] = 'https://github.com/ahmedayyad-dev/AyyadMusicBot'

_pool = ConnectionPool.from_url(
    'redis://localhost:6379',
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    health_check_interval=30,
    retry_on_timeout=True,
    max_connections=200,
)

database = aioredis.Redis(connection_pool=_pool)

bot = Client(
    'bot',
    API_ID,
    API_HASH,
    bot_token=TOKEN,
    fetch_replies=False,
    fetch_topics=False,
    fetch_stories=False,
    fetch_stickers=False,
    plugins=dict(root='plugins/bot'),
)
