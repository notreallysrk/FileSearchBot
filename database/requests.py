# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.requests")

class RequestRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.requests

    async def create_request(
        self,
        request_id: str,
        user_id: int,
        description: str,
        logger_chat_id: int,
        logger_message_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": request_id,
            "user_id": user_id,
            "first_name": first_name or "",
            "username": username or None,
            "description": description,
            "status": "pending",
            "created_at": now,
            "completed_at": None,
            "completed_by": None,
            "logger_chat_id": logger_chat_id,
            "logger_message_id": logger_message_id,
        }
        await self.collection.insert_one(doc)
        logger.info("Request created: id=%s user_id=%d", request_id, user_id)
        return doc

    async def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": request_id})

    async def complete_request(
        self, request_id: str, completed_by: int
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        doc = await self.collection.find_one_and_update(
            {"_id": request_id, "status": "pending"},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now,
                    "completed_by": completed_by,
                }
            },
            return_document=True,
        )
        if doc:
            logger.info("Request completed: id=%s by=%d", request_id, completed_by)
        return doc

    async def count_by_status(self, status: Optional[str] = None) -> int:
        query = {"status": status} if status else {}
        return await self.collection.count_documents(query)
