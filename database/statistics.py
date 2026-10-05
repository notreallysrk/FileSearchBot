# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.statistics")

GLOBAL_STATS_ID = "global_stats"

class StatisticsRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.statistics
        self.db = db

    async def increment_counter(self, field: str, amount: int = 1) -> None:
        await self.collection.update_one(
            {"_id": GLOBAL_STATS_ID},
            {"$inc": {field: amount}},
            upsert=True,
        )

    async def get_raw_stats(self) -> Dict[str, Any]:
        doc = await self.collection.find_one({"_id": GLOBAL_STATS_ID})
        return doc or {}

    async def aggregate_full_stats(self, total_indexed_files: int = 0) -> Dict[str, Any]:
        registered_users = await self.db.users.count_documents({})
        blocked_users = await self.db.blocked_users.count_documents({})
        total_requests = await self.db.requests.count_documents({})
        pending_requests = await self.db.requests.count_documents({"status": "pending"})
        completed_requests = await self.db.requests.count_documents({"status": "completed"})

        raw = await self.get_raw_stats()
        successful_deliveries = raw.get("successful_deliveries", 0)
        failed_deliveries = raw.get("failed_deliveries", 0)
        searches_performed = raw.get("searches_performed", 0)

        return {
            "registered_users": registered_users,
            "total_files_indexed": total_indexed_files,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "completed_requests": completed_requests,
            "blocked_users": blocked_users,
            "searches_performed": searches_performed,
        }
