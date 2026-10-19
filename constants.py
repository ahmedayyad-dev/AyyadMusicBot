# pylint: disable=C0114
import os
import tomllib
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

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
URL_CACHE_CAP: Final[int] = 20 * 60
SEARCH_MAX_RESULTS: Final[int] = 10
QUEUE_LIMIT: Final[int] = 50
DOWNLOAD_TOKEN_TTL: Final[int] = 30 * 60
SOURCE_URL: Final[str] = 'https://github.com/ahmedayyad-dev/AyyadMusicBot'
