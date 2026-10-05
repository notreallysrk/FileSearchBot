# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import re
import unicodedata
from typing import List, Set

TOKEN_CLEAN_RE = re.compile(r"[^\w\s#]", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("_", " ").replace("-", " ")

    normalized = unicodedata.normalize("NFKC", text).lower()

    cleaned = TOKEN_CLEAN_RE.sub(" ", normalized)

    return WHITESPACE_RE.sub(" ", cleaned).strip()

def extract_search_tokens(text: str, max_tokens: int = 20) -> List[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    tokens: List[str] = []
    seen: Set[str] = set()

    for raw_token in normalized.split(" "):
        if not raw_token:
            continue

        if raw_token.startswith("#"):
            stripped = raw_token.lstrip("#")
            if stripped and stripped not in seen:
                seen.add(stripped)
                tokens.append(stripped)
            if raw_token not in seen:
                seen.add(raw_token)
                tokens.append(raw_token)
        else:
            if raw_token not in seen:
                seen.add(raw_token)
                tokens.append(raw_token)

        if len(tokens) >= max_tokens:
            break

    return tokens

def truncate_text(text: str, max_length: int = 35, suffix: str = "...") -> str:
    if not text:
        return ""
    clean = " ".join(text.split())
    if len(clean) <= max_length:
        return clean
    cutoff = max_length - len(suffix)
    return clean[:cutoff].rstrip() + suffix
