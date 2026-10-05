# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logging import get_logger

logger = get_logger("database.indexes")

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    logger.info("Ensuring database indexes...")

    await db.users.create_index([("last_active", DESCENDING)], background=True)
    await db.users.create_index([("is_blocked", ASCENDING)], background=True)

    await db.blocked_users.create_index([("blocked_at", DESCENDING)], background=True)

    await db.requests.create_index([("status", ASCENDING), ("created_at", DESCENDING)], background=True)
    await db.requests.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], background=True)

    await db.token_registry.create_index([("file_id", ASCENDING)], background=True)

    await db.token_registry.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)

    logger.info("Database indexes successfully verified and created")
