# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Any, Set, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.settings")

class SystemSettingsRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.settings
        self._maintenance_mode: bool = False
        self._allowed_chats: Set[int] = set()

    @property
    def is_maintenance_mode(self) -> bool:
        return self._maintenance_mode

    @property
    def allowed_chats(self) -> Set[int]:
        return set(self._allowed_chats)

    def is_chat_allowed(self, chat_id: int, default_files_group: int = 0) -> bool:
        if default_files_group and chat_id == default_files_group:
            return True
        return chat_id in self._allowed_chats

    async def load(self) -> None:
        try:
            doc = await self.collection.find_one({"_id": "system_config"})
            if doc:
                self._maintenance_mode = bool(doc.get("maintenance_mode", False))
                raw_chats = doc.get("allowed_chats", [])
                self._allowed_chats = {int(x) for x in raw_chats if str(x).lstrip("-").isdigit()}
                logger.info(
                    "Loaded system settings: maintenance_mode=%s, allowed_chats=%d",
                    self._maintenance_mode,
                    len(self._allowed_chats),
                )
            else:
                await self.collection.update_one(
                    {"_id": "system_config"},
                    {
                        "$setOnInsert": {
                            "maintenance_mode": False,
                            "allowed_chats": [],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                    upsert=True,
                )
                self._maintenance_mode = False
                self._allowed_chats = set()
        except Exception as exc:
            logger.warning("Failed to load system settings from MongoDB: %s", exc)

    async def set_maintenance_mode(self, enabled: bool) -> None:
        self._maintenance_mode = enabled
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            await self.collection.update_one(
                {"_id": "system_config"},
                {"$set": {"maintenance_mode": enabled, "updated_at": now_iso}},
                upsert=True,
            )
            logger.info("Maintenance mode set to: %s", enabled)
        except Exception as exc:
            logger.error("Failed to update maintenance mode in MongoDB: %s", exc)

    async def allow_chat(self, chat_id: int) -> bool:
        if chat_id in self._allowed_chats:
            return False
        self._allowed_chats.add(chat_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            await self.collection.update_one(
                {"_id": "system_config"},
                {"$addToSet": {"allowed_chats": chat_id}, "$set": {"updated_at": now_iso}},
                upsert=True,
            )
            logger.info("Added chat %d to allowed groups list", chat_id)
            return True
        except Exception as exc:
            logger.error("Failed to add allowed chat in MongoDB: %s", exc)
            return False

    async def disallow_chat(self, chat_id: int) -> bool:
        if chat_id not in self._allowed_chats:
            return False
        self._allowed_chats.discard(chat_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            await self.collection.update_one(
                {"_id": "system_config"},
                {"$pull": {"allowed_chats": chat_id}, "$set": {"updated_at": now_iso}},
                upsert=True,
            )
            logger.info("Removed chat %d from allowed groups list", chat_id)
            return True
        except Exception as exc:
            logger.error("Failed to remove allowed chat from MongoDB: %s", exc)
            return False
