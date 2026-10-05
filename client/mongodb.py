# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from config import Settings
from utils.logging import get_logger
from utils.exceptions import DatabaseError

logger = get_logger("mongodb")

class MongoDB:

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._connected: bool = False

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise DatabaseError("MongoDB client is not initialized. Call connect() first.")
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise DatabaseError("MongoDB database is not initialized. Call connect() first.")
        return self._db

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        if self._connected and self._client is not None:
            return

        logger.info("Connecting to MongoDB database: %s", self.settings.DATABASE_NAME)

        try:
            import dns.resolver
            default_resolver = dns.resolver.get_default_resolver()
            public_dns = ["1.1.1.1", "8.8.8.8", "8.8.4.4"]
            for dns_ip in public_dns:
                if dns_ip not in default_resolver.nameservers:
                    default_resolver.nameservers.append(dns_ip)
        except Exception:
            pass

        for attempt in range(1, max_retries + 1):
            try:
                self._client = AsyncIOMotorClient(
                    self.settings.MONGO_URI,
                    maxPoolSize=50,
                    minPoolSize=5,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=10000,
                    retryWrites=True,
                    uuidRepresentation="standard",
                )
                self._db = self._client[self.settings.DATABASE_NAME]

                await self._client.admin.command("ping")
                self._connected = True
                logger.info("Successfully connected to MongoDB")
                return

            except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
                logger.warning(
                    "MongoDB connection attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))
                else:
                    self._connected = False
                    logger.error("Failed to connect to MongoDB after %d attempts", max_retries)
                    raise DatabaseError(f"Could not connect to MongoDB: {exc}") from exc
            except Exception as exc:
                self._connected = False
                logger.exception("Unexpected error connecting to MongoDB: %s", exc)
                raise DatabaseError(f"Unexpected MongoDB connection failure: {exc}") from exc

    async def ping(self) -> bool:
        if not self._client or not self._connected:
            return False
        try:
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            logger.info("Closing MongoDB connection pool")
            self._client.close()
            self._client = None
            self._db = None
            self._connected = False
            logger.info("MongoDB connection closed")
