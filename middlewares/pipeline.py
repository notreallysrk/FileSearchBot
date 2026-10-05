# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import time
from typing import Optional, Dict, List, Union

from pyrogram import Client, enums
from pyrogram.enums import ChatType
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import Settings
from database.users import UserRepository
from database.blocked_users import BlockedUserRepository
from database.settings import SystemSettingsRepository
from keyboards.inline import get_maintenance_keyboard, get_open_pm_keyboard
from lang.manager import tr
from services.cache_manager import TTLCache
from services.event_logger import EventLoggerService
from services.subscription import SubscriptionService
from utils.logging import get_logger

logger = get_logger("middlewares.pipeline")

class TokenBucket:
    __slots__ = ("tokens", "last_update", "rate", "burst")

    def __init__(self, rate: float, burst: int):
        self.tokens: float = float(burst)
        self.last_update: float = time.monotonic()
        self.rate: float = rate
        self.burst: int = burst

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        self.tokens = min(float(self.burst), self.tokens + (elapsed / self.rate))
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

class SecurityPipeline:
    def __init__(
        self,
        settings: Settings,
        user_repo: UserRepository,
        blocked_repo: BlockedUserRepository,
        subscription_service: SubscriptionService,
        system_settings_repo: Optional[SystemSettingsRepository] = None,
        event_logger: Optional[EventLoggerService] = None,
    ):
        self.settings = settings
        self.user_repo = user_repo
        self.blocked_repo = blocked_repo
        self.subscription_service = subscription_service
        self.system_settings_repo = system_settings_repo
        self.event_logger = event_logger

        self.rate = settings.RATE_LIMIT_RATE
        self.burst = settings.RATE_LIMIT_BURST
        self._buckets: TTLCache[TokenBucket] = TTLCache(maxsize=10000, default_ttl=3600.0)
        self._user_messages: Dict[int, List[float]] = {}
        self._synced_users: Dict[int, float] = {}
        self._warned_rate_limit: Dict[int, float] = {}

    async def check_message(
        self, client: Client, message: Message, require_sub: bool = False
    ) -> bool:
        user = message.from_user
        if not user or user.is_bot:
            return True

        user_id = user.id
        is_owner = self.settings.is_owner(user_id)

        exempt_chats = {
            self.settings.LOGGER_GROUP_ID,
            self.settings.FILES_GROUP_ID,
            self.settings.file_request_group_id,
        }
        is_exempt_chat = message.chat.id in exempt_chats
        is_interactive_text = bool(message.text and (message.chat.type == ChatType.PRIVATE or message.text.startswith("/")))

        if not is_owner and not is_exempt_chat and is_interactive_text:
            now = time.monotonic()
            recent = [t for t in self._user_messages.get(user_id, []) if now - t <= 10.0]
            recent.append(now)
            self._user_messages[user_id] = recent

            if len(recent) >= 10:
                logger.warning("Spam detected from user %d (%d msgs in 10s). Blocking.", user_id, len(recent))
                await self.blocked_repo.block_user(
                    user_id=user_id,
                    blocked_by=0,
                    reason=f"Auto-ban: sent {len(recent)} messages in 10s",
                )
                self.blocked_repo.warned_blocks.add(user_id)

                if self.event_logger:
                    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"
                    asyncio.create_task(
                        self.event_logger.notify_spammer_blocked(
                            user_id=user_id,
                            full_name=full_name,
                            username=user.username,
                            msg_count=len(recent),
                        )
                    )

                lang = await self.user_repo.get_language(user_id)
                await message.reply_text(
                    tr("spammer_blocked_user_notice", lang),
                    parse_mode=enums.ParseMode.HTML,
                )
                return False

        if await self.blocked_repo.is_blocked(user_id):
            if user_id not in self.blocked_repo.warned_blocks:
                self.blocked_repo.warned_blocks.add(user_id)
                lang = await self.user_repo.get_language(user_id)
                await message.reply_text(tr("user_blocked", lang), parse_mode=enums.ParseMode.HTML)
            return False

        if not is_owner:
            bucket = self._buckets.get(str(user_id))
            if bucket is None:
                bucket = TokenBucket(rate=self.rate, burst=self.burst)
                self._buckets.set(str(user_id), bucket)

            if not bucket.consume():
                logger.warning("Rate limit exceeded for user %d", user_id)
                now_mono = time.monotonic()
                last_warn = self._warned_rate_limit.get(user_id, 0.0)
                if now_mono - last_warn > 30.0:
                    self._warned_rate_limit[user_id] = now_mono
                    lang = await self.user_repo.get_language(user_id)
                    await message.reply_text(tr("rate_limit_warning", lang))
                return False

        if self.system_settings_repo and self.system_settings_repo.is_maintenance_mode and not is_owner:
            lang = await self.user_repo.get_language(user_id)
            support_url = self.settings.SUPPORT_GROUP_URL or self.settings.BACKUP_CHANNEL_URL or "https://t.me/social_bots"
            kb = get_maintenance_keyboard(support_url=support_url, lang=lang)
            await message.reply_text(tr("maintenance_notice", lang), reply_markup=kb, parse_mode=enums.ParseMode.HTML)
            return False

        chat_type = message.chat.type
        if chat_type in (ChatType.GROUP, ChatType.SUPERGROUP):
            if not message.text and not is_exempt_chat:
                return False
            require_sub = False
        elif chat_type == ChatType.CHANNEL:
            if not is_exempt_chat:
                return False

        now_wall = time.time()
        if now_wall - self._synced_users.get(user_id, 0.0) > 900.0:
            self._synced_users[user_id] = now_wall
            asyncio.create_task(
                self._safe_upsert_user(user_id, user.first_name, user.username)
            )

        if require_sub and not is_owner and self.settings.SUBSCRIBE:
            user_files = await self.user_repo.get_files_received(user_id)
            if user_files >= 5:
                missing = await self.subscription_service.get_missing_channels(client, user_id)
                if missing:
                    lang = await self.user_repo.get_language(user_id)
                    keyboard = self.subscription_service.build_subscription_keyboard(missing, lang=lang)
                    first_name = escape_html(user.first_name or "Friend")
                    prompt = tr("force_sub_prompt", lang, first_name=first_name)
                    await message.reply_text(prompt, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
                    return False

        return True

    async def check_callback(self, client: Client, callback: CallbackQuery) -> bool:
        user = callback.from_user
        if not user or user.is_bot:
            return True

        user_id = user.id
        is_owner = self.settings.is_owner(user_id)

        now = time.monotonic()
        recent = [t for t in self._user_messages.get(user_id, []) if now - t <= 10.0]
        recent.append(now)
        self._user_messages[user_id] = recent

        if len(recent) >= 10 and not is_owner:
            await self.blocked_repo.block_user(
                user_id=user_id,
                blocked_by=0,
                reason=f"Auto-ban: sent {len(recent)} callbacks in 10s",
            )
            self.blocked_repo.warned_blocks.add(user_id)
            await callback.answer("⛔ Blocked for spamming!", show_alert=True)
            return False

        if await self.blocked_repo.is_blocked(user_id):
            if user_id not in self.blocked_repo.warned_blocks:
                self.blocked_repo.warned_blocks.add(user_id)
                await callback.answer("⛔ Access Denied: You are blocked.", show_alert=True)
            return False

        if self.system_settings_repo and self.system_settings_repo.is_maintenance_mode and not is_owner:
            await callback.answer("🛠️ The bot is currently under maintenance. Please wait!", show_alert=True)
            return False

        return True

    async def _safe_upsert_user(
        self, user_id: int, first_name: Optional[str], username: Optional[str]
    ) -> None:
        try:
            lang = await self.user_repo.get_language(user_id)
            is_new = await self.user_repo.upsert_user(
                user_id=user_id,
                first_name=first_name or "",
                username=username,
                lang=lang,
            )
            if is_new and self.event_logger:
                await self.event_logger.notify_new_user(
                    user_id=user_id,
                    full_name=first_name or "User",
                    username=username,
                )
        except Exception as exc:
            logger.error("Background user upsert failed for %d: %s", user_id, exc)
