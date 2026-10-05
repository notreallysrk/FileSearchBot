# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import asyncio
from typing import List, Tuple, Optional, Union, Dict, Any
from pyrogram import Client, enums
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, RPCError, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup
from keyboards.inline import get_subscription_keyboard
from motor.motor_asyncio import AsyncIOMotorDatabase

from config import Settings
from lang.manager import tr
from services.cache_manager import TTLCache
from utils.logging import get_logger

logger = get_logger("subscription")

DB_SETTING_KEY = "force_subscription"

class SubscriptionService:
    def __init__(self, settings: Settings, event_logger: Optional[Any] = None):
        self.settings = settings
        self.event_logger = event_logger
        self._cache: TTLCache[bool] = TTLCache(maxsize=10000, default_ttl=300.0)
        self._semaphore = asyncio.Semaphore(5)
        self._channels: List[Dict[str, Any]] = [
            {"channel": ch, "invite_link": self.settings.SUBSCRIBE_INVITE_LINKS.get(str(ch))}
            for ch in self.settings.SUBSCRIBE
        ]

    def is_cached_subscribed(self, user_id: int) -> bool:
        return bool(self._cache.get(f"sub:{user_id}"))

    def mark_subscribed(self, user_id: int, ttl: float = 300.0) -> None:
        self._cache.set(f"sub:{user_id}", True, ttl=ttl)

    def clear_cache(self, user_id: Optional[int] = None) -> None:
        if user_id is not None:
            self._cache.delete(f"sub:{user_id}")
        else:
            self._cache = TTLCache(maxsize=10000, default_ttl=300.0)

    async def load_from_db(self, db: AsyncIOMotorDatabase) -> None:
        try:
            doc = await db.settings.find_one({"_id": DB_SETTING_KEY})
            if doc and "channels" in doc:
                self._channels = doc.get("channels", [])
                logger.info("Loaded %d force-subscription channels from MongoDB", len(self._channels))
                return

            initial_channels = []
            for ch in self.settings.SUBSCRIBE:
                link = self.settings.SUBSCRIBE_INVITE_LINKS.get(str(ch))
                initial_channels.append({"channel": ch, "invite_link": link})

            self._channels = initial_channels
            if initial_channels:
                await db.settings.update_one(
                    {"_id": DB_SETTING_KEY},
                    {"$set": {"channels": initial_channels}},
                    upsert=True,
                )
                logger.info("Saved %d initial config channels to MongoDB settings", len(initial_channels))
        except Exception as exc:
            logger.warning("Could not load force-subscription from MongoDB: %s", exc)

    async def add_channel(
        self,
        db: AsyncIOMotorDatabase,
        channel: Union[str, int],
        invite_link: Optional[str] = None,
    ) -> bool:
        ch_str = str(channel).strip()
        for item in self._channels:
            if str(item.get("channel")) == ch_str:
                if invite_link and item.get("invite_link") != invite_link:
                    item["invite_link"] = invite_link
                    await db.settings.update_one(
                        {"_id": DB_SETTING_KEY},
                        {"$set": {"channels": self._channels}},
                        upsert=True,
                    )
                    self.clear_cache()
                    return True
                return False

        new_entry = {"channel": channel, "invite_link": invite_link}
        self._channels.append(new_entry)
        await db.settings.update_one(
            {"_id": DB_SETTING_KEY},
            {"$set": {"channels": self._channels}},
            upsert=True,
        )
        self.clear_cache()
        logger.info("Added force-subscription channel: %s", channel)
        return True

    async def remove_channel(
        self,
        db: AsyncIOMotorDatabase,
        channel: Union[str, int],
    ) -> bool:
        ch_str = str(channel).strip()
        initial_len = len(self._channels)
        self._channels = [
            item for item in self._channels if str(item.get("channel")) != ch_str
        ]

        if len(self._channels) < initial_len:
            await db.settings.update_one(
                {"_id": DB_SETTING_KEY},
                {"$set": {"channels": self._channels}},
                upsert=True,
            )
            self.clear_cache()
            logger.info("Removed force-subscription channel: %s", channel)
            return True
        return False

    def get_channels(self) -> List[Dict[str, Any]]:
        return list(self._channels)

    async def get_missing_channels(
        self, bot: Client, user_id: int, ignore_cache: bool = False
    ) -> List[Tuple[Union[str, int], str]]:
        if not self._channels:
            return []

        if not ignore_cache and self.is_cached_subscribed(user_id):
            return []

        missing: List[Tuple[Union[str, int], str]] = []

        async def check_channel(entry: Dict[str, Any]) -> Optional[Tuple[Union[str, int], str]]:
            channel = entry.get("channel")
            if not channel:
                return None
            async with self._semaphore:
                try:
                    member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
                    status = member.status
                    is_member = False
                    if status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER):
                        is_member = True
                    elif status == ChatMemberStatus.RESTRICTED:
                        is_member = bool(getattr(member, "is_member", True))

                    if not is_member:
                        invite_link = entry.get("invite_link") or await self._resolve_channel_url(bot, channel)
                        return (channel, invite_link)
                    return None
                except UserNotParticipant:
                    invite_link = entry.get("invite_link") or await self._resolve_channel_url(bot, channel)
                    return (channel, invite_link)
                except FloodWait as exc:
                    await asyncio.sleep(getattr(exc, "value", 2) + 1)
                    return None
                except Exception as exc:
                    logger.warning("Could not check channel %s: %s", channel, exc)
                    if self.event_logger:
                        err_text = (
                            f"⚠️ <b>Subscription Check Warning</b>\n"
                            f"Channel: <code>{channel}</code>\n"
                            f"Error: <code>{type(exc).__name__}: {str(exc)}</code>\n"
                            f"<i>Skipping force-subscription for this channel.</i>"
                        )
                        asyncio.create_task(self.event_logger.log_event(err_text))
                    return None

        tasks = [check_channel(entry) for entry in self._channels]
        results = await asyncio.gather(*tasks)

        for res in results:
            if res is not None:
                missing.append(res)

        if not missing:
            self.mark_subscribed(user_id)
        else:
            self.clear_cache(user_id)

        return missing

    async def _resolve_channel_url(self, bot: Client, channel: Union[str, int]) -> str:
        if isinstance(channel, str) and channel.startswith("@"):
            return f"https://t.me/{channel[1:]}"

        ch_str = str(channel)
        if ch_str in self.settings.SUBSCRIBE_INVITE_LINKS:
            return self.settings.SUBSCRIBE_INVITE_LINKS[ch_str]

        try:
            chat = await bot.get_chat(channel)
            if getattr(chat, "invite_link", None):
                return chat.invite_link
            link = await bot.create_chat_invite_link(chat_id=channel)
            return link.invite_link
        except Exception:
            return f"https://t.me/c/{str(channel).replace('-100', '')}"

    def build_subscription_keyboard(
        self, missing: List[Tuple[Union[str, int], str]], lang: str = "en"
    ) -> InlineKeyboardMarkup:
        return get_subscription_keyboard(missing, lang=lang)
