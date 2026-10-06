# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import asyncio
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from pyrogram import Client, enums
from pyrogram.errors import FloodWait

from config import Settings
from lang.manager import tr
from utils.logging import get_logger

logger = get_logger("event_logger")

class EventLoggerService:
    def __init__(self, settings: Settings, bot: Optional[Client] = None):
        self.settings = settings
        self.bot = bot
        self._last_ram_alert: float = 0.0

    def set_bot(self, bot: Client) -> None:
        self.bot = bot

    async def log_event(self, text: str) -> None:
        if not self.bot or not self.settings.LOGGER_GROUP_ID:
            return
        try:
            await self.bot.send_message(
                chat_id=self.settings.LOGGER_GROUP_ID,
                text=text,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except FloodWait as exc:
            wait_sec = getattr(exc, "value", None) or getattr(exc, "x", 3)
            logger.warning("FloodWait in event_logger: waiting %ds", wait_sec)
            await asyncio.sleep(wait_sec + 1)
            try:
                await self.bot.send_message(
                    chat_id=self.settings.LOGGER_GROUP_ID,
                    text=text,
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.warning("Retry logging failed: %s", e)
        except Exception as exc:
            logger.warning("Failed to send notification to logger group: %s", exc)

    async def notify_bot_started(
        self, bot_username: str, version: int, total_files: int
    ) -> None:
        # Kept for backward compatibility with client/bots.py.
        # Startup logging is intentionally disabled; user /start events
        # are logged through notify_user_started() instead.
        return

    async def notify_user_started(
        self, user_id: int, full_name: str, username: Optional[str] = None
    ) -> None:
        clean_name = (full_name or "User").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        username_display = f"@{username}" if username else "@None"
        mention = f'<a href="tg://user?id={user_id}">{clean_name}</a>'
        text = (
            f"{mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n"
            f"ᴜsᴇʀ ɪᴅ :\n"
            f"{user_id}\n"
            f"ᴜsᴇʀɴᴀᴍᴇ : {username_display}"
        )
        await self.log_event(text)

    async def notify_serious_error(
        self, error_type: str, details: str, user_id: Optional[int] = None
    ) -> None:
        user_line = f"\n• <b>User ID:</b> <code>{user_id}</code>" if user_id else ""
        clean_details = details.replace("<", "&lt;").replace(">", "&gt;")[:1500]
        time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        text = tr(
            "log_serious_error",
            "en",
            error_type=error_type,
            user_line=user_line,
            details=clean_details,
            time_str=time_str,
        )
        await self.log_event(text)

    async def notify_new_user(
        self, user_id: int, full_name: str, username: Optional[str] = None
    ) -> None:
        uname_line = f"@{username}" if username else "<i>None</i>"
        clean_name = full_name.replace("<", "&lt;").replace(">", "&gt;")
        time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        text = tr(
            "log_new_user",
            "en",
            user_id=user_id,
            clean_name=clean_name,
            uname_line=uname_line,
            time_str=time_str,
        )
        await self.log_event(text)

    async def notify_high_ram(self, ram_mb: float, threshold_mb: float = 400.0) -> None:
        now = time.monotonic()
        if now - self._last_ram_alert < 1800.0:
            return
        self._last_ram_alert = now
        time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        text = tr(
            "log_high_ram",
            "en",
            ram_mb=ram_mb,
            ram_gb=(ram_mb / 1024.0),
            threshold_mb=threshold_mb,
            time_str=time_str,
        )
        await self.log_event(text)

    async def notify_spammer_blocked(
        self, user_id: int, full_name: str, username: Optional[str], msg_count: int
    ) -> None:
        uname_line = f"@{username}" if username else "<i>None</i>"
        clean_name = full_name.replace("<", "&lt;").replace(">", "&gt;")
        time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        text = tr(
            "log_spammer_blocked",
            "en",
            user_id=user_id,
            clean_name=clean_name,
            uname_line=uname_line,
            msg_count=msg_count,
            time_str=time_str,
        )
        await self.log_event(text)
