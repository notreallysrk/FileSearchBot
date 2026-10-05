# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Optional, TypeVar, Generic

T = TypeVar("T")

class TTLCache(Generic[T]):

    def __init__(self, maxsize: int = 1000, default_ttl: float = 300.0):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        if key not in self._cache:
            return None

        val, expiry = self._cache[key]
        if time.monotonic() > expiry:
            del self._cache[key]
            return None

        self._cache.move_to_end(key)
        return val

    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        expiry = time.monotonic() + (ttl if ttl is not None else self.default_ttl)

        if key in self._cache:
            del self._cache[key]

        while len(self._cache) >= self.maxsize:
            self._cache.popitem(last=False)

        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
