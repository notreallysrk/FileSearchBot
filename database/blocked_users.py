# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from utils.logging import get_logger

logger = get_logger("database.blocked_users")

class BlockedUserRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.blocked_users
        self.users_collection = db.users
        self._blocked_ids: set[int] = set()
        self.warned_blocks: set[int] = set()
        self._cache_loaded: bool = False

    async def load_cache(self) -> None:
        try:
            cursor = self.collection.find({}, projection={"_id": 1})
            docs = await cursor.to_list(length=100000)
            self._blocked_ids = {doc["_id"] for doc in docs if "_id" in doc}
            self._cache_loaded = True
            logger.info("Pre-warmed %d blocked user IDs in memory", len(self._blocked_ids))
        except Exception as exc:
            logger.warning("Could not pre-warm blocked users cache: %s", exc)

    async def block_user(
        self,
        user_id: int,
        blocked_by: int,
        username: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "username": username,
                    "blocked_by": blocked_by,
                    "reason": reason,
                    "blocked_at": now,
                }
            },
            upsert=True,
        )

        await self.users_collection.update_one(
            {"_id": user_id},
            {"$set": {"is_blocked": True}},
        )
        self._blocked_ids.add(user_id)
        is_new = result.upserted_id is not None
        logger.info("User blocked: id=%d by=%d is_new=%s", user_id, blocked_by, is_new)
        return is_new

    async def unblock_user(self, user_id: int) -> bool:
        result = await self.collection.delete_one({"_id": user_id})
        await self.users_collection.update_one(
            {"_id": user_id},
            {"$set": {"is_blocked": False}},
        )
        self._blocked_ids.discard(user_id)
        self.warned_blocks.discard(user_id)
        was_blocked = result.deleted_count > 0
        if was_blocked:
            logger.info("User unblocked: id=%d", user_id)
        return was_blocked

    async def is_blocked(self, user_id: int) -> bool:
        if self._cache_loaded:
            return user_id in self._blocked_ids
        doc = await self.collection.find_one({"_id": user_id}, projection={"_id": 1})
        if doc is not None:
            self._blocked_ids.add(user_id)
            return True
        return False

    async def count_blocked(self) -> int:
        return await self.collection.count_documents({})

    async def get_blocked_page(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        skip = max(0, (page - 1) * page_size)
        total = await self.count_blocked()
        cursor = self.collection.find({}).sort("blocked_at", DESCENDING).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total
