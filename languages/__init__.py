# pylint: disable=C0114
from core.config import bot, database
from languages.ar import STRINGS as AR_STRINGS
from languages.en import STRINGS as EN_STRINGS
from languages.uz import STRINGS as UZ_STRINGS

LANGUAGES: dict[str, dict[str, str]] = {
    'ar': AR_STRINGS,
    'en': EN_STRINGS,
    'uz': UZ_STRINGS,
}
DEFAULT_LANGUAGE = 'ar'

_USER_LANG_CACHE: dict[int, str] = {}
_GROUP_LANG_CACHE: dict[int, str] = {}


def _strings_for(code: str | None) -> dict[str, str]:
    if code in LANGUAGES:
        return LANGUAGES[code]
    return LANGUAGES[DEFAULT_LANGUAGE]


def text(code: str | None, key: str, **kwargs) -> str:
    template = _strings_for(code).get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


async def get_language(target_id: int, user_id: int | None = None) -> str:
    if user_id is not None and target_id < 0:
        cached_user = _USER_LANG_CACHE.get(user_id)
        if cached_user in LANGUAGES:
            return cached_user
        cached_group = _GROUP_LANG_CACHE.get(target_id)
        if cached_group in LANGUAGES:
            return cached_group
        async with database.pipeline() as pipe:
            pipe.get(f'{bot.me.id}:user:{user_id}:lang')
            pipe.get(f'{bot.me.id}:group:{target_id}:lang')
            results = await pipe.execute()
        if results[0] in LANGUAGES:
            _USER_LANG_CACHE[user_id] = results[0]
            return results[0]
        if results[1] in LANGUAGES:
            _GROUP_LANG_CACHE[target_id] = results[1]
            return results[1]
        return DEFAULT_LANGUAGE

    if target_id < 0:
        cached = _GROUP_LANG_CACHE.get(target_id)
        if cached in LANGUAGES:
            return cached
        lang = await database.get(f'{bot.me.id}:group:{target_id}:lang')
        if lang in LANGUAGES:
            _GROUP_LANG_CACHE[target_id] = lang
            return lang
        return DEFAULT_LANGUAGE

    cached = _USER_LANG_CACHE.get(target_id)
    if cached in LANGUAGES:
        return cached
    lang = await database.get(f'{bot.me.id}:user:{target_id}:lang')
    if lang in LANGUAGES:
        _USER_LANG_CACHE[target_id] = lang
        return lang
    return DEFAULT_LANGUAGE


async def set_language(target_id: int, lang_code: str) -> None:
    if lang_code not in LANGUAGES:
        return
    if target_id < 0:
        _GROUP_LANG_CACHE[target_id] = lang_code
    else:
        _USER_LANG_CACHE[target_id] = lang_code
    await database.set(
        f'{bot.me.id}:group:{target_id}:lang'
        if target_id < 0
        else f'{bot.me.id}:user:{target_id}:lang',
        lang_code,
    )
