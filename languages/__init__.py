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
        async with database.pipeline() as pipe:
            pipe.get(f'{bot.me.id}:user:{user_id}:lang')
            pipe.get(f'{bot.me.id}:group:{target_id}:lang')
            results = await pipe.execute()
        user_lang = results[0]
        if user_lang in LANGUAGES:
            return user_lang
        group_lang = results[1]
        if group_lang in LANGUAGES:
            return group_lang
        return DEFAULT_LANGUAGE

    lang = await database.get(
        f'{bot.me.id}:group:{target_id}:lang'
        if target_id < 0
        else f'{bot.me.id}:user:{target_id}:lang'
    )
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


async def set_language(target_id: int, lang_code: str) -> None:
    if lang_code not in LANGUAGES:
        return
    await database.set(
        f'{bot.me.id}:group:{target_id}:lang'
        if target_id < 0
        else f'{bot.me.id}:user:{target_id}:lang',
        lang_code,
    )
