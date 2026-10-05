# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Optional, Any
from pyrogram import Client, enums
from pyrogram.types import CallbackQuery

from config import Settings
from database.blocked_users import BlockedUserRepository
from database.users import UserRepository
from keyboards.pagination import PaginationManager
from lang.manager import tr
from plugins.block import handle_blocked_page_callback
from plugins.help import handle_help_callback, handle_start_menu_callback
from plugins.lang import handle_language_callback
from plugins.request import ACTIVE_REQUEST_USERS
from plugins.scan import handle_scan_pause_callback, handle_scan_resume_callback, handle_scan_stop_callback
from services.request_manager import RequestManager
from services.search_engine import SearchEngine
from services.subscription import SubscriptionService
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.callbacks")

async def handle_callback_query(
    client: Client,
    callback: CallbackQuery,
    settings: Settings,
    pagination_manager: PaginationManager,
    search_engine: SearchEngine,
    request_manager: RequestManager,
    subscription_service: SubscriptionService,
    user_repo: UserRepository,
    blocked_repo: BlockedUserRepository,
    scanner_service: Any,
    lang: str = "en",
) -> None:
    data = callback.data or ""
    user = callback.from_user
    if not user:
        return

    if data == "noop":
        await callback.answer()
        return

    if data == "help_menu":
        await handle_help_callback(client, callback, settings, lang=lang)
        return

    if data == "start_menu":
        await handle_start_menu_callback(client, callback, settings, lang=lang)
        return

    if data == "make_request":
        ACTIVE_REQUEST_USERS.add(user.id)
        await callback.answer()
        if callback.message:
            await callback.message.reply_text(tr("request_prompt", lang), parse_mode=enums.ParseMode.HTML)
        return

    if data == "explore":
        all_files = search_engine.get_all_files()[:100]
        if not all_files:
            await callback.answer(tr("search_no_results", lang, query="Explore"), show_alert=True)
            return

        session = pagination_manager.create_session(
            user_id=user.id,
            query="Explore Library",
            file_ids=[f.id for f in all_files],
        )
        keyboard = await pagination_manager.build_search_keyboard(
            session=session,
            page=1,
            search_engine=search_engine,
            lang=lang,
        )
        text = tr("search_results_header", lang, query="Explore Library", total=len(all_files), page=1, pages=session.total_pages)
        if callback.message:
            try:
                await callback.message.reply_text(text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
            except Exception:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
        await callback.answer()
        return

    if data.startswith("flt:"):
        parts = data.split(":")
        if len(parts) != 3:
            await callback.answer()
            return
        _, session_id, media_type = parts
        session = pagination_manager.get_session(session_id)
        if not session:
            await callback.answer(tr("session_expired", lang), show_alert=True)
            return
        if session.user_id != user.id:
            await callback.answer(tr("session_not_yours", lang), show_alert=True)
            return

        session.apply_filter(media_type, search_engine)
        keyboard = await pagination_manager.build_search_keyboard(
            session=session,
            page=1,
            search_engine=search_engine,
            lang=lang,
        )
        clean_query = escape_html(session.query)
        total = session.total_items
        pages = session.total_pages
        filter_badge = f" [{media_type.upper()}]" if session.current_filter else ""
        new_text = tr("search_results_header", lang, query=f"{clean_query}{filter_badge}", total=total, page=1, pages=pages)
        try:
            if callback.message:
                await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
            await callback.answer()
        except Exception:
            await callback.answer()
        return

    if data == "confirm_sub":
        missing = await subscription_service.get_missing_channels(client, user.id)
        if missing:
            await callback.answer(tr("force_sub_still_missing", lang), show_alert=True)
            return
        await callback.answer(tr("force_sub_verified", lang), show_alert=True)
        await handle_start_menu_callback(client, callback, settings, lang=lang)
        return

    if data.startswith("sp:"):
        parts = data.split(":")
        if len(parts) != 3:
            await callback.answer("Malformed request.", show_alert=True)
            return

        _, session_id, page_str = parts
        try:
            page = int(page_str)
        except ValueError:
            await callback.answer("Invalid page.", show_alert=True)
            return

        session = pagination_manager.get_session(session_id)
        if not session:
            await callback.answer(tr("session_expired", lang), show_alert=True)
            return

        if session.user_id != user.id:
            await callback.answer(tr("session_not_yours", lang), show_alert=True)
            return

        if page < 1 or page > session.total_pages:
            await callback.answer()
            return

        keyboard = await pagination_manager.build_search_keyboard(
            session=session,
            page=page,
            search_engine=search_engine,
            lang=lang,
        )

        clean_query = escape_html(session.query)
        total = session.total_items
        pages = session.total_pages
        new_text = tr("search_results_header", lang, query=clean_query, total=total, page=page, pages=pages)

        try:
            if callback.message:
                await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
            await callback.answer()
        except Exception as exc:
            logger.warning("Failed to edit pagination message: %s", exc)
            await callback.answer()
        return

    if data.startswith("req_up:"):
        if not settings.is_owner(user.id):
            await callback.answer("⛔ Only configured bot owners can complete requests!", show_alert=True)
            return

        parts = data.split(":")
        if len(parts) != 2:
            await callback.answer("Malformed request callback.", show_alert=True)
            return

        request_id = parts[1]
        success, msg = await request_manager.mark_request_completed(
            bot=client,
            request_id=request_id,
            completed_by_id=user.id,
        )
        await callback.answer(msg, show_alert=True)
        return

    if data.startswith("blk_pg:"):
        await handle_blocked_page_callback(client, callback, settings, blocked_repo)
        return

    if data.startswith("scan:pause:"):
        await handle_scan_pause_callback(client, callback, settings, scanner_service)
        return

    if data.startswith("scan:resume:"):
        await handle_scan_resume_callback(client, callback, settings, scanner_service)
        return

    if data.startswith("scan:stop:"):
        await handle_scan_stop_callback(client, callback, settings, scanner_service)
        return

    if data.startswith("set_lang:"):
        await handle_language_callback(client, callback, user_repo)
        return

    await callback.answer()
