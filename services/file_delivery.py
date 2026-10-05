# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import asyncio
from typing import Tuple, Optional, List
from pyrogram import Client, enums
from pyrogram.errors import FloodWait, UserIsBlocked, RPCError

from database.users import UserRepository
from database.blocked_users import BlockedUserRepository
from lang.manager import tr
from services.file_tokens import FileTokenService
from services.search_engine import SearchEngine, IndexedFile
from services.statistics_manager import StatisticsManager
from utils.exceptions import TokenError, UserBlockedError
from utils.logging import get_logger

logger = get_logger("services.file_delivery")

class FileDeliveryService:
    def __init__(
        self,
        token_service: FileTokenService,
        search_engine: SearchEngine,
        user_repo: UserRepository,
        blocked_repo: BlockedUserRepository,
        stats_manager: StatisticsManager,
        auto_delete_seconds: int = 300,
    ):
        self.token_service = token_service
        self.search_engine = search_engine
        self.user_repo = user_repo
        self.blocked_repo = blocked_repo
        self.stats_manager = stats_manager
        self.auto_delete_seconds = auto_delete_seconds

    async def deliver_file_by_token(
        self,
        bot: Client,
        user_id: int,
        token: str,
        lang: str = "en",
    ) -> Tuple[bool, str]:
        if await self.blocked_repo.is_blocked(user_id):
            raise UserBlockedError()

        try:
            file_id = await self.token_service.resolve_token(token)
        except TokenError as exc:
            return False, exc.user_facing

        file_record = self.search_engine.get_file(file_id)
        if not file_record:
            return False, tr("delivery_file_missing", lang)

        delivered = await self._send_media(bot, user_id, file_record, lang=lang)

        if delivered:
            self.stats_manager.record_delivery_success()
            await self.user_repo.increment_files_received(user_id)
            return True, "Success"
        else:
            self.search_engine.remove_file(file_record.id)
            self.stats_manager.record_delivery_failure()
            return False, tr("internal_error", lang)

    async def deliver_random_files(
        self,
        bot: Client,
        user_id: int,
        count: int = 1,
        file_type: Optional[str] = None,
        lang: str = "en",
    ) -> Tuple[int, str]:
        if await self.blocked_repo.is_blocked(user_id):
            raise UserBlockedError()

        safe_count = max(1, min(10, count))
        files = self.search_engine.get_random_files(count=safe_count, file_type=file_type)
        if not files:
            return 0, tr("search_no_results", lang, query="Random")

        delivered_count = 0
        for idx, file_record in enumerate(files):
            delivered = await self._send_media(bot, user_id, file_record, lang=lang)
            if delivered:
                delivered_count += 1
                self.stats_manager.record_delivery_success()
                await self.user_repo.increment_files_received(user_id)
            else:
                self.search_engine.remove_file(file_record.id)

            if idx < len(files) - 1:
                await asyncio.sleep(2.0)

        if delivered_count > 0:
            return delivered_count, tr("delivery_random_success", lang, count=delivered_count)
        return 0, tr("internal_error", lang)

    async def _send_media(self, bot: Client, user_id: int, file_record: IndexedFile, lang: str = "en") -> bool:
        tg_file_id = file_record.delivery_file_id or file_record.master_file_id
        base_caption = file_record.caption or file_record.file_name or ""

        delete_notice = tr("delivery_delete_notice", lang)
        caption = f"{base_caption}{delete_notice}"
        if len(caption) > 1024:
            cutoff = 1020 - len(delete_notice)
            caption = f"{base_caption[:cutoff]}...{delete_notice}"

        for attempt in range(2):
            try:
                sent_msg = None
                if tg_file_id:
                    try:
                        sent_msg = await bot.send_cached_media(
                            chat_id=user_id,
                            file_id=tg_file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML,
                        )
                    except Exception:
                        sent_msg = None

                if not sent_msg and file_record.source_chat_id and file_record.source_message_id:
                    sent_msg = await bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=file_record.source_chat_id,
                        message_id=file_record.source_message_id,
                        caption=caption,
                        parse_mode=enums.ParseMode.HTML,
                    )

                if sent_msg:
                    msg_id = getattr(sent_msg, "id", None) or getattr(sent_msg, "message_id", None)
                    if msg_id:
                        asyncio.create_task(
                            self._schedule_message_deletion(bot=bot, chat_id=user_id, message_id=msg_id, delay=self.auto_delete_seconds),
                            name=f"del_file_{user_id}_{msg_id}",
                        )
                    return True

                return False

            except FloodWait as exc:
                wait_sec = getattr(exc, "value", None) or getattr(exc, "x", 3)
                await asyncio.sleep(wait_sec + 1)
                if attempt == 0:
                    continue
                return False
            except UserIsBlocked:
                return False
            except RPCError:
                if attempt == 0 and file_record.source_chat_id and file_record.source_message_id:
                    tg_file_id = None
                    continue
                return False
            except Exception as exc:
                logger.exception("Unexpected error delivering file %s to %d: %s", file_record.id, user_id, exc)
                return False

        return False

    async def _schedule_message_deletion(
        self, bot: Client, chat_id: int, message_id: int, delay: int = 300
    ) -> None:
        try:
            await asyncio.sleep(delay)
            await bot.delete_messages(chat_id=chat_id, message_ids=message_id)
        except Exception:
            pass
