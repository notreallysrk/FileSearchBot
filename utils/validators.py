# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import re
from typing import Optional

SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
CHANNEL_USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{4,32}$")

def is_valid_token_format(token: Optional[str]) -> bool:
    if not token or not isinstance(token, str):
        return False
    return bool(SAFE_TOKEN_RE.match(token))

def is_valid_telegram_id(user_id: Any) -> bool:
    try:
        val = int(user_id)
        return val > 0
    except (ValueError, TypeError):
        return False

def is_valid_channel_identifier(identifier: Any) -> bool:
    if isinstance(identifier, int):
        return identifier < 0
    if isinstance(identifier, str):
        if identifier.startswith("-"):
            try:
                return int(identifier) < 0
            except ValueError:
                return False
        return bool(CHANNEL_USERNAME_RE.match(identifier))
    return False
