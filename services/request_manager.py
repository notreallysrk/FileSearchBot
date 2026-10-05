# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import uuid
from typing import Optional, Dict, Any, Tuple
from pyrogram import Client, enums

from config import Settings
from database.requests import RequestRepository
from database.users import UserRepository
from keyboards.inline import get_request_admin_keyboard
from lang.manager import tr
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("request_manager")

class RequestManager:
    def __init__(self, settings: Settings, request_repo: RequestRepository, user_repo: Optional[UserRepository] = None):
        self.settings = settings
        self.request_repo = request_repo
        self.user_repo = user_repo

    async def submit_request(
        self,
        bot: Client,
        user_id: int,
        description: str,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        req_id = uuid.uuid4().hex[:12]
        clean_desc = escape_html(description.strip())
        user_display = escape_html(first_name or "User")
        uname_line = f"<b>Username:</b> @{username}\n" if username else ""

        logger_text = tr(
            "request_logger_new",
            "en",
            user_display=user_display,
            user_id=user_id,
            uname_line=uname_line,
            clean_desc=clean_desc,
            req_id=req_id,
        )

        keyboard = get_request_admin_keyboard(req_id, lang="en")
        target_group = self.settings.file_request_group_id
        logger_msg = await bot.send_message(
            chat_id=target_group,
            text=logger_text,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML,
        )

        msg_id = getattr(logger_msg, "id", None) or getattr(logger_msg, "message_id", None)
        doc = await self.request_repo.create_request(
            request_id=req_id,
            user_id=user_id,
            description=description.strip(),
            logger_chat_id=target_group,
            logger_message_id=msg_id,
            first_name=first_name,
            username=username,
        )
        return doc

    async def mark_request_completed(
        self,
        bot: Client,
        request_id: str,
        completed_by_id: int,
    ) -> Tuple[bool, str]:
        doc = await self.request_repo.complete_request(request_id, completed_by=completed_by_id)
        if not doc:
            return False, tr("request_not_found_or_done", "en")

        user_id = doc["user_id"]
        description = doc.get("description", "")
        clean_desc = escape_html(description)

        try:
            completed_text = tr(
                "request_logger_completed",
                "en",
                user_id=user_id,
                clean_desc=clean_desc,
                completed_by_id=completed_by_id,
            )
            await bot.edit_message_text(
                chat_id=doc["logger_chat_id"],
                message_id=doc["logger_message_id"],
                text=completed_text,
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception as exc:
            logger.warning("Could not update logger message for request %s: %s", request_id, exc)

        lang = "en"
        if self.user_repo:
            lang = await self.user_repo.get_language(user_id)

        notify_text = tr("request_completed_notify", lang, description=clean_desc)
        try:
            await bot.send_message(
                chat_id=user_id,
                text=notify_text,
                parse_mode=enums.ParseMode.HTML,
            )
            logger.info("Notified user %d for completed request %s", user_id, request_id)
        except Exception as exc:
            logger.warning("Could not notify requester %d: %s", user_id, exc)

        return True, tr("request_marked_success", "en")
