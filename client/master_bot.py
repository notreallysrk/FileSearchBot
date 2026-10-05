# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Any, Optional
from pyrogram import Client, filters, enums
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from keyboards.inline import get_group_search_keyboard, get_open_pm_keyboard, get_random_dual_keyboard
from lang.manager import tr

from plugins.start import handle_start_command
from plugins.help import handle_help_command
from plugins.search import handle_search_query, handle_explore_command, handle_storage_file_received
from plugins.request import (
    handle_request_command,
    handle_cancel_command,
    handle_request_description_received,
    handle_group_request_description_received,
    handle_hashtag_request,
    is_user_requesting,
    is_group_requesting,
)
from plugins.block import handle_block_command, handle_unblock_command, handle_list_blocked_command
from plugins.stats import handle_stats_command
from plugins.scan import handle_scan_command
from plugins.file_delivery import handle_random_command
from plugins.admin import (
    handle_restart_command,
    handle_maintain_command,
    handle_vars_command,
    handle_setvar_command,
    handle_allow_command,
    handle_disallow_command,
    handle_allowed_command,
)
from plugins.lang import handle_language_command
from plugins.callbacks import handle_callback_query
from plugins.errors import handle_client_error

def register_master_handlers(client: Client, ecosystem: Any) -> None:
    pipeline = ecosystem.security_pipeline

    async def on_message_handler(c: Client, m: Message) -> None:
        user = m.from_user
        if not user or user.is_bot:
            return

        user_lang = await ecosystem.user_repo.get_language(user.id)
        text = (m.text or "").strip()
        is_cmd = text.startswith("/")
        cmd_name = text.split()[0][1:].split("@")[0].lower() if is_cmd else ""

        require_sub = not is_cmd and not is_user_requesting(user.id) and m.chat.type == ChatType.PRIVATE
        allowed = await pipeline.check_message(c, m, require_sub=require_sub)
        if not allowed:
            return

        try:
            if is_cmd:
                if m.chat.type != ChatType.PRIVATE and cmd_name in ("start", "help"):
                    guide_text = tr("group_usage_guide", user_lang)
                    kb = get_open_pm_keyboard(ecosystem.settings.MASTER_BOT_USERNAME, lang=user_lang)
                    await m.reply_text(guide_text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
                    return

                if cmd_name == "start":
                    await handle_start_command(
                        client=c,
                        message=m,
                        settings=ecosystem.settings,
                        subscription_service=ecosystem.subscription_service,
                        user_repo=ecosystem.user_repo,
                        event_logger=ecosystem.event_logger,
                        file_delivery_service=ecosystem.file_delivery_service,
                        lang=user_lang,
                    )
                elif cmd_name == "search":
                    parts = text.split(maxsplit=1)
                    search_query = parts[1].strip() if len(parts) > 1 else ""
                    if search_query:
                        await handle_search_query(
                            client=c,
                            message=m,
                            search_engine=ecosystem.search_engine,
                            pagination_manager=ecosystem.pagination_manager,
                            stats_manager=ecosystem.stats_manager,
                            request_manager=ecosystem.request_manager,
                            lang=user_lang,
                            query=search_query,
                        )
                    else:
                        prompt_text = (
                            "🔍 <b>Search Files</b>\n\n"
                            "• Use <code>/search &lt;name&gt;</code> to find files\n"
                            "• Or click below to search privately in Bot PM."
                        )
                        kb = get_group_search_keyboard(ecosystem.settings.MASTER_BOT_USERNAME, lang=user_lang)
                        await m.reply_text(prompt_text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
                elif cmd_name == "help":
                    await handle_help_command(c, m, ecosystem.settings, lang=user_lang)
                elif cmd_name == "explore":
                    await handle_explore_command(
                        client=c,
                        message=m,
                        search_engine=ecosystem.search_engine,
                        pagination_manager=ecosystem.pagination_manager,
                        lang=user_lang,
                    )
                elif cmd_name == "random":
                    parts = text.split(maxsplit=1)
                    raw_cnt = parts[1].strip() if len(parts) > 1 else "1"
                    cnt = int(raw_cnt) if raw_cnt.isdigit() else 1
                    cnt = max(1, min(10, cnt))

                    if ecosystem.settings.is_dual_bot:
                        kb = get_random_dual_keyboard(
                            delivery_username=ecosystem.settings.delivery_username,
                            count=cnt,
                            lang=user_lang,
                        )
                        await m.reply_text(
                            tr("random_dual_redirect", user_lang),
                            reply_markup=kb,
                            parse_mode=enums.ParseMode.HTML,
                        )
                    else:
                        await handle_random_command(
                            client=c,
                            message=m,
                            settings=ecosystem.settings,
                            file_delivery_service=ecosystem.file_delivery_service,
                            subscription_service=ecosystem.subscription_service,
                            user_repo=ecosystem.user_repo,
                            lang=user_lang,
                        )
                elif cmd_name == "request":
                    await handle_request_command(
                        client=c,
                        message=m,
                        request_manager=ecosystem.request_manager,
                        lang=user_lang,
                    )
                elif cmd_name == "cancel":
                    await handle_cancel_command(c, m, lang=user_lang)
                elif cmd_name in ("lang", "language"):
                    await handle_language_command(c, m, lang=user_lang)
                elif cmd_name == "stats":
                    await handle_stats_command(
                        client=c,
                        message=m,
                        settings=ecosystem.settings,
                        start_time=ecosystem.start_time,
                    )
                elif cmd_name == "scan":
                    await handle_scan_command(
                        client=c,
                        message=m,
                        settings=ecosystem.settings,
                        scanner_service=ecosystem.scanner_service,
                        delivery_client=ecosystem.delivery_bot if ecosystem.settings.is_dual_bot else None,
                    )
                elif cmd_name == "block":
                    await handle_block_command(c, m, ecosystem.settings, ecosystem.blocked_repo)
                elif cmd_name == "unblock":
                    await handle_unblock_command(c, m, ecosystem.settings, ecosystem.blocked_repo)
                elif cmd_name == "blocked":
                    await handle_list_blocked_command(c, m, ecosystem.settings, ecosystem.blocked_repo)
                elif cmd_name == "vars":
                    await handle_vars_command(c, m, ecosystem.settings)
                elif cmd_name in ("setvar", "setvars"):
                    await handle_setvar_command(c, m, ecosystem.settings, ecosystem=ecosystem)
                elif cmd_name == "allow":
                    await handle_allow_command(c, m, ecosystem.settings, ecosystem.system_settings_repo)
                elif cmd_name == "disallow":
                    await handle_disallow_command(c, m, ecosystem.settings, ecosystem.system_settings_repo)
                elif cmd_name == "allowed":
                    await handle_allowed_command(c, m, ecosystem.settings, ecosystem.system_settings_repo)
                elif cmd_name == "maintain":
                    await handle_maintain_command(c, m, ecosystem.settings, ecosystem.system_settings_repo)
                elif cmd_name == "restart":
                    await handle_restart_command(c, m, ecosystem.settings, ecosystem=ecosystem)
                return

            if m.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
                has_media = bool(m.document or m.video or m.audio or m.animation or m.photo)
                if has_media:
                    is_allowed = False
                    if ecosystem.system_settings_repo:
                        is_allowed = ecosystem.system_settings_repo.is_chat_allowed(m.chat.id, ecosystem.settings.FILES_GROUP_ID)
                    elif ecosystem.settings.is_allowed_chat(m.chat.id):
                        is_allowed = True
                    if is_allowed:
                        await handle_storage_file_received(c, m, ecosystem.manifest_manager, ecosystem.stats_manager)
                    return

                text = (m.text or "").strip()
                if not text:
                    return

                if is_group_requesting(m.chat.id, user.id):
                    handled = await handle_group_request_description_received(
                        client=c,
                        message=m,
                        request_manager=ecosystem.request_manager,
                        lang=user_lang,
                    )
                    if handled:
                        return

                if "#request" in text.lower():
                    await handle_hashtag_request(
                        client=c,
                        message=m,
                        request_manager=ecosystem.request_manager,
                        lang=user_lang,
                    )
                    return

                return

            if m.chat.type == ChatType.PRIVATE:
                if is_user_requesting(user.id):
                    handled = await handle_request_description_received(
                        client=c,
                        message=m,
                        request_manager=ecosystem.request_manager,
                        lang=user_lang,
                    )
                    if handled:
                        return

                await handle_search_query(
                    client=c,
                    message=m,
                    settings=ecosystem.settings,
                    search_engine=ecosystem.search_engine,
                    pagination_manager=ecosystem.pagination_manager,
                    stats_manager=ecosystem.stats_manager,
                    request_manager=ecosystem.request_manager,
                    event_logger=ecosystem.event_logger,
                    lang=user_lang,
                )
        except Exception as exc:
            await handle_client_error(c, m, exc, ecosystem.event_logger)

    async def on_callback_query_handler(c: Client, cb: CallbackQuery) -> None:
        user = cb.from_user
        if not user:
            return

        user_lang = await ecosystem.user_repo.get_language(user.id)
        allowed = await pipeline.check_callback(c, cb)
        if not allowed:
            return

        try:
            await handle_callback_query(
                client=c,
                callback=cb,
                settings=ecosystem.settings,
                pagination_manager=ecosystem.pagination_manager,
                search_engine=ecosystem.search_engine,
                request_manager=ecosystem.request_manager,
                subscription_service=ecosystem.subscription_service,
                user_repo=ecosystem.user_repo,
                blocked_repo=ecosystem.blocked_repo,
                scanner_service=ecosystem.scanner_service,
                lang=user_lang,
            )
        except Exception as exc:
            await handle_client_error(c, cb, exc, ecosystem.event_logger)

    client.add_handler(MessageHandler(on_message_handler))
    client.add_handler(CallbackQueryHandler(on_callback_query_handler))
