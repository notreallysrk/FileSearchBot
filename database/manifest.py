# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.manifest")

SETTING_KEY = "file_manifest"

class ManifestRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.settings

    async def get_pointer(self) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": SETTING_KEY})

    async def update_pointer(
        self,
        chat_id: int,
        message_id: int,
        file_id: str,
        version: int,
    ) -> None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": SETTING_KEY},
            {
                "$set": {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "file_id": file_id,
                    "version": version,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        logger.info(
            "Updated manifest pointer in MongoDB: version=%d chat_id=%d msg_id=%d",
            version,
            chat_id,
            message_id,
        )
