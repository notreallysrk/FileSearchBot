# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.token_registry")

class TokenRegistryRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.token_registry

    async def save_token(
        self,
        token: str,
        file_id: str,
        expires_at: Optional[datetime] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": token},
            {
                "$set": {
                    "file_id": file_id,
                    "created_at": now,
                    "expires_at": expires_at,
                },
                "$setOnInsert": {
                    "access_count": 0,
                },
            },
            upsert=True,
        )

    async def resolve_token(self, token: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one_and_update(
            {"_id": token},
            {"$inc": {"access_count": 1}},
            return_document=True,
        )
        if not doc:
            return None

        expires_at = doc.get("expires_at")
        if expires_at:

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                logger.info("Resolved token has expired: %s", token[:8])
                return None

        return doc

    async def delete_token(self, token: str) -> bool:
        res = await self.collection.delete_one({"_id": token})
        return res.deleted_count > 0
