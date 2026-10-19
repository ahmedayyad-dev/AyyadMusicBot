# pylint: disable=C0114
from languages.ar import STRINGS

LANGUAGES: dict[str, dict[str, str]] = {'ar': STRINGS}


def available_languages() -> list[str]:
    return list(LANGUAGES)


def strings_for(code: str | None) -> dict[str, str]:
    if code in LANGUAGES:
        return LANGUAGES[code]
    return LANGUAGES['ar']


def text(code: str | None, key: str, **kwargs) -> str:
    template = strings_for(code).get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
