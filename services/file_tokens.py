# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from database.files import TokenRegistryRepository
from services.cache_manager import TTLCache
from utils.exceptions import TokenInvalidError, TokenExpiredError
from utils.validators import is_valid_token_format
from utils.logging import get_logger

logger = get_logger("file_tokens")

class FileTokenService:

    def __init__(
        self,
        token_repo: Optional[TokenRegistryRepository] = None,
        cache_size: int = 5000,
        default_ttl: int = 0,
    ):
        self.token_repo = token_repo
        self.default_ttl = default_ttl

        self._token_cache: TTLCache[str] = TTLCache(maxsize=cache_size, default_ttl=3600.0)

    async def create_token(
        self,
        file_id: str,
        expires_seconds: Optional[int] = None,
    ) -> str:

        token = secrets.token_urlsafe(16)

        ttl = self.default_ttl if expires_seconds is None else expires_seconds
        expires_at: Optional[datetime] = None
        if ttl > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        self._token_cache.set(token, file_id, ttl=float(ttl) if ttl > 0 else 86400.0)

        if self.token_repo is not None:
            await self.token_repo.save_token(token, file_id, expires_at=expires_at)

        return token

    async def resolve_token(self, token: str) -> str:

        if not is_valid_token_format(token):
            raise TokenInvalidError("Malformed deep-link token format.")

        cached_file_id = self._token_cache.get(token)
        if cached_file_id:
            return cached_file_id

        if self.token_repo is None:
            raise TokenInvalidError("Token not found or repository unconfigured.")

        doc = await self.token_repo.resolve_token(token)
        if not doc:
            raise TokenInvalidError("Token not found or has expired.")

        file_id = doc.get("file_id")
        if not file_id:
            raise TokenInvalidError("Invalid file record associated with token.")

        self._token_cache.set(token, file_id, ttl=3600.0)
        return file_id
