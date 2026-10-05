# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import traceback
from typing import Optional, Union
from pyrogram import Client, enums
from pyrogram.errors import (
    FloodWait,
    MessageNotModified,
    UserIsBlocked,
    BadRequest,
    RPCError,
)
from pyrogram.types import Message, CallbackQuery

from services.event_logger import EventLoggerService
from utils.exceptions import AppError
from utils.logging import get_logger

logger = get_logger("plugins.errors")

async def handle_client_error(
    client: Client,
    update: Union[Message, CallbackQuery],
    exception: Exception,
    event_logger: Optional[EventLoggerService] = None,
) -> bool:
    if isinstance(exception, FloodWait):
        wait_sec = getattr(exception, "value", None) or getattr(exception, "x", 5)
        logger.warning("Kurigram FloodWait triggered: waiting %ss", wait_sec)
        await asyncio.sleep(min(wait_sec + 1, 15))
        return True

    if isinstance(exception, (UserIsBlocked, MessageNotModified)):
        return True

    if isinstance(exception, AppError):
        logger.warning("Application error handled: %s", exception.message)
        if isinstance(update, Message):
            try:
                await update.reply_text(f"⚠️ {exception.user_facing}", parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
        elif isinstance(update, CallbackQuery):
            try:
                await update.answer(f"⚠️ {exception.user_facing}", show_alert=True)
            except Exception:
                pass
        return True

    logger.exception("Unhandled exception processing update: %s", exception)

    user_id = None
    if update.from_user:
        user_id = update.from_user.id

    if event_logger:
        tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        asyncio.create_task(
            event_logger.notify_serious_error(
                error_type=type(exception).__name__,
                details=f"{exception}\n\nTraceback:\n{tb}",
                user_id=user_id,
            )
        )

    if isinstance(update, Message):
        try:
            await update.reply_text(
                "❌ An unexpected internal error occurred. Our engineers have been alerted.",
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            pass
    elif isinstance(update, CallbackQuery):
        try:
            await update.answer(
                "❌ An unexpected error occurred. Please try again later.",
                show_alert=True,
            )
        except Exception:
            pass

    return True
