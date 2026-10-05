# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import math
from typing import Optional
from pyrogram import Client, enums
from pyrogram.types import Message, CallbackQuery

from config import Settings
from database.blocked_users import BlockedUserRepository
from database.users import UserRepository
from keyboards.inline import get_blocked_users_keyboard
from lang.manager import tr
from utils.formatting import escape_html
from utils.validators import is_valid_telegram_id
from utils.logging import get_logger

logger = get_logger("plugins.block")

async def handle_block_command(
    client: Client,
    message: Message,
    settings: Settings,
    blocked_repo: BlockedUserRepository,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    text_parts = (message.text or "").strip().split(maxsplit=2)
    raw_args = text_parts[1:] if len(text_parts) > 1 else []
    target_id: Optional[int] = None
    reason: Optional[str] = None

    if raw_args and is_valid_telegram_id(raw_args[0]):
        target_id = int(raw_args[0])
        if len(raw_args) > 1:
            reason = raw_args[1]
    elif message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        if raw_args:
            reason = " ".join(raw_args)

    if not target_id:
        await message.reply_text(tr("admin_block_usage", "en"), parse_mode=enums.ParseMode.HTML)
        return

    if settings.is_owner(target_id):
        await message.reply_text(tr("admin_block_owner_error", "en"), parse_mode=enums.ParseMode.HTML)
        return

    is_new = await blocked_repo.block_user(
        user_id=target_id,
        blocked_by=user.id,
        reason=reason,
    )

    if is_new:
        await message.reply_text(tr("admin_block_success", "en", user_id=target_id), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text(tr("admin_block_already", "en", user_id=target_id), parse_mode=enums.ParseMode.HTML)

async def handle_unblock_command(
    client: Client,
    message: Message,
    settings: Settings,
    blocked_repo: BlockedUserRepository,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    text_parts = (message.text or "").strip().split(maxsplit=1)
    args = text_parts[1].strip() if len(text_parts) > 1 else ""
    target_id: Optional[int] = None

    if is_valid_telegram_id(args):
        target_id = int(args)
    elif message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id

    if not target_id:
        await message.reply_text(tr("admin_unblock_usage", "en"), parse_mode=enums.ParseMode.HTML)
        return

    was_blocked = await blocked_repo.unblock_user(target_id)
    if was_blocked:
        await message.reply_text(tr("admin_unblock_success", "en", user_id=target_id), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text(tr("admin_unblock_not_found", "en", user_id=target_id), parse_mode=enums.ParseMode.HTML)

async def handle_list_blocked_command(
    client: Client,
    message: Message,
    settings: Settings,
    blocked_repo: BlockedUserRepository,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    items, total = await blocked_repo.get_blocked_page(page=1, page_size=10)
    if not items:
        await message.reply_text(tr("admin_blocked_empty", "en"), parse_mode=enums.ParseMode.HTML)
        return

    total_pages = max(1, math.ceil(total / 10))
    text = _format_blocked_page(items, page=1, total_pages=total_pages, total=total)
    keyboard = get_blocked_users_keyboard(page=1, total_pages=total_pages)

    await message.reply_text(text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

async def handle_blocked_page_callback(
    client: Client,
    callback: CallbackQuery,
    settings: Settings,
    blocked_repo: BlockedUserRepository,
) -> None:
    user = callback.from_user
    if not user or not settings.is_owner(user.id):
        await callback.answer("Owner command only.", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 2:
        return

    try:
        page = int(parts[1])
    except ValueError:
        return

    items, total = await blocked_repo.get_blocked_page(page=page, page_size=10)
    total_pages = max(1, math.ceil(total / 10))

    if page < 1 or page > total_pages:
        await callback.answer()
        return

    text = _format_blocked_page(items, page=page, total_pages=total_pages, total=total)
    keyboard = get_blocked_users_keyboard(page=page, total_pages=total_pages)

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
    await callback.answer()

def _format_blocked_page(items: list, page: int, total_pages: int, total: int) -> str:
    lines = [tr("admin_blocked_header", "en", page=page, total_pages=total_pages, total_count=total)]
    for doc in items:
        uid = doc.get("_id")
        dt = doc.get("blocked_at")
        dt_str = dt.strftime("%Y-%m-%d %H:%M") if hasattr(dt, "strftime") else "N/A"
        reason = escape_html(doc.get("reason") or "No reason specified")
        lines.append(f"• <code>{uid}</code> (<i>{dt_str}</i>) - {reason}")
    return "\n".join(lines)
