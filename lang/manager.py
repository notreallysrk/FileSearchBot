# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Any, Dict

from lang.en import STRINGS as EN_STRINGS
from lang.hi import STRINGS as HI_STRINGS

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": EN_STRINGS,
    "hi": HI_STRINGS,
}

def tr(key: str, lang: str = "en", **kwargs: Any) -> str:
    table = TRANSLATIONS.get(lang, EN_STRINGS)
    template = table.get(key, EN_STRINGS.get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
