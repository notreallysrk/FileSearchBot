# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.users")

class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users
        self._lang_cache: Dict[int, str] = {}

    async def upsert_user(
        self,
        user_id: int,
        first_name: str,
        username: Optional[str] = None,
        lang: str = "en",
    ) -> bool:
        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "first_name": first_name or "",
                    "username": username or None,
                    "last_active": now,
                },
                "$setOnInsert": {
                    "joined_at": now,
                    "is_blocked": False,
                    "files_received": 0,
                    "lang": lang,
                },
            },
            upsert=True,
        )
        if user_id not in self._lang_cache:
            self._lang_cache[user_id] = lang
        return result.upserted_id is not None

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": user_id})

    async def count_users(self) -> int:
        return await self.collection.count_documents({})

    async def increment_files_received(self, user_id: int, count: int = 1) -> None:
        await self.collection.update_one(
            {"_id": user_id},
            {"$inc": {"files_received": count}},
        )

    async def get_files_received(self, user_id: int) -> int:
        doc = await self.collection.find_one({"_id": user_id}, projection={"files_received": 1})
        if doc and "files_received" in doc:
            return int(doc["files_received"] or 0)
        return 0

    async def set_blocked_status(self, user_id: int, is_blocked: bool) -> None:
        await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"is_blocked": is_blocked}},
        )

    async def get_language(self, user_id: int) -> str:
        if user_id in self._lang_cache:
            return self._lang_cache[user_id]
        doc = await self.collection.find_one({"_id": user_id}, projection={"lang": 1})
        lang = (doc.get("lang") if doc else None) or "en"
        self._lang_cache[user_id] = lang
        return lang

    async def set_language(self, user_id: int, lang: str) -> None:
        self._lang_cache[user_id] = lang
        await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"lang": lang}},
            upsert=True,
        )
