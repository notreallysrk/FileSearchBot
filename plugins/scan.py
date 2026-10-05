# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import re
import uuid
from typing import Optional

from pyrogram import Client, enums
from pyrogram.enums import ChatType
from pyrogram.types import Message, CallbackQuery

from config import Settings
from keyboards.inline import get_scanner_keyboard
from lang.manager import tr
from services.scanner import ScannerService
from utils.logging import get_logger

logger = get_logger("plugins.scan")

SCAN_RANGE_PATTERN = re.compile(r"^/scan(?:@\w+)?\s+(-?\d+)(?:(?:\s*[-:]\s*|\s+to\s+|\s+)(-?\d+))?$", re.IGNORECASE)

async def handle_scan_command(
    client: Client,
    message: Message,
    settings: Settings,
    scanner_service: ScannerService,
    delivery_client: Optional[Client] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text(
            tr("admin_scan_private_error", "en"),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    text = (message.text or "").strip()
    match = SCAN_RANGE_PATTERN.match(text)
    if not match:
        await message.reply_text(
            tr("admin_scan_invalid_format", "en"),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    val1 = max(1, abs(int(match.group(1))))
    val2 = max(1, abs(int(match.group(2)))) if match.group(2) else 1
    start_id, end_id = min(val1, val2), max(val1, val2)

    active_session = scanner_service.get_active_session(message.chat.id)
    if active_session and not active_session.is_stopped:
        await message.reply_text(
            tr("admin_scan_already_running", "en", start_id=active_session.start_id, end_id=active_session.end_id),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    fetch_client = delivery_client or client
    session_id = uuid.uuid4().hex[:8]
    total_msgs = end_id - start_id + 1

    kb = get_scanner_keyboard(session_id=session_id)
    initial_text = tr(
        "admin_scan_progress_template",
        "en",
        checked=0,
        total=total_msgs,
        pct=0.0,
        saved=0,
        current_id=start_id,
        status="Starting scan...",
    )
    initial_msg = await message.reply_text(
        initial_text,
        reply_markup=kb,
        parse_mode=enums.ParseMode.HTML,
    )

    await scanner_service.start_scan(
        master_bot=client,
        delivery_bot=fetch_client,
        chat_id=message.chat.id,
        start_id=start_id,
        end_id=end_id,
        status_message=initial_msg,
        session_id=session_id,
    )

async def handle_scan_pause_callback(
    client: Client,
    query: CallbackQuery,
    settings: Settings,
    scanner_service: ScannerService,
) -> None:
    user = query.from_user
    if not user or not settings.is_owner(user.id):
        await query.answer("Unauthorized", show_alert=True)
        return

    session_id = query.data.split(":")[2]
    session = scanner_service.get_session_by_id(session_id)
    if not session or session.is_stopped:
        await query.answer("Scan ended", show_alert=True)
        return

    session.pause()
    await session.update_progress_message(client, note="Paused by owner.")
    await query.answer(tr("admin_scan_paused", "en"))

async def handle_scan_resume_callback(
    client: Client,
    query: CallbackQuery,
    settings: Settings,
    scanner_service: ScannerService,
) -> None:
    user = query.from_user
    if not user or not settings.is_owner(user.id):
        await query.answer("Unauthorized", show_alert=True)
        return

    session_id = query.data.split(":")[2]
    session = scanner_service.get_session_by_id(session_id)
    if not session or session.is_stopped:
        await query.answer("Scan ended", show_alert=True)
        return

    session.resume()
    await session.update_progress_message(client, note="Resumed by owner.")
    await query.answer(tr("admin_scan_resumed", "en"))

async def handle_scan_stop_callback(
    client: Client,
    query: CallbackQuery,
    settings: Settings,
    scanner_service: ScannerService,
) -> None:
    user = query.from_user
    if not user or not settings.is_owner(user.id):
        await query.answer("Unauthorized", show_alert=True)
        return

    session_id = query.data.split(":")[2]
    session = scanner_service.get_session_by_id(session_id)
    if not session or session.is_stopped:
        await query.answer("Scan ended", show_alert=True)
        return

    session.stop()
    await session.update_progress_message(client, note="Stopped by owner.", finished=True)
    await query.answer(tr("admin_scan_stopped", "en"))
