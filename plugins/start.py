# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import asyncio
from typing import Optional, Any
from pyrogram import Client, enums
from pyrogram.types import Message

from config import Settings
from database.users import UserRepository
from keyboards.inline import get_start_keyboard
from lang.manager import tr
from services.event_logger import EventLoggerService
from services.subscription import SubscriptionService
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.start")

async def handle_start_command(
    client: Client,
    message: Message,
    settings: Settings,
    subscription_service: SubscriptionService,
    user_repo: Optional[UserRepository] = None,
    event_logger: Optional[EventLoggerService] = None,
    file_delivery_service: Optional[Any] = None,
    lang: str = "en",
) -> None:
    user = message.from_user
    if not user:
        return

    if event_logger:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"
        asyncio.create_task(
            event_logger.notify_user_started(
                user_id=user.id,
                full_name=full_name,
                username=user.username,
            )
        )

    if user_repo and event_logger:
        is_new = await user_repo.upsert_user(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username,
            lang=lang,
        )
        if is_new:
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"
            asyncio.create_task(
                event_logger.notify_new_user(
                    user_id=user.id,
                    full_name=full_name,
                    username=user.username,
                )
            )

    first_name = escape_html(user.first_name or "Friend")
    text_parts = (message.text or "").strip().split(maxsplit=1)
    arg = text_parts[1].strip() if len(text_parts) > 1 else None

    if arg and arg != "group":
        if not settings.is_dual_bot and file_delivery_service:
            if not settings.is_owner(user.id) and user_repo and subscription_service and settings.SUBSCRIBE:
                user_files = await user_repo.get_files_received(user.id)
                if user_files >= 5:
                    missing = await subscription_service.get_missing_channels(client, user.id)
                    if missing:
                        keyboard = subscription_service.build_subscription_keyboard(missing, lang=lang)
                        await message.reply_text(
                            tr("force_sub_prompt", lang, first_name=first_name),
                            reply_markup=keyboard,
                            parse_mode=enums.ParseMode.HTML,
                        )
                        return

            try:
                success, msg = await file_delivery_service.deliver_file_by_token(
                    bot=client,
                    user_id=user.id,
                    token=arg,
                    lang=lang,
                )
                if not success:
                    await message.reply_text(f"⚠️ {msg}", parse_mode=enums.ParseMode.HTML)
            except Exception as exc:
                logger.exception("Error delivering file on master bot: %s", exc)
                await message.reply_text(tr("internal_error", lang), parse_mode=enums.ParseMode.HTML)
            return

        delivery_url = f"https://t.me/{settings.delivery_username}?start={arg}"
        await message.reply_text(
            tr(
                "file_delivery_dual_redirect",
                lang,
                url=delivery_url,
                delivery_username=settings.delivery_username,
            ),
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    if not settings.is_owner(user.id) and settings.SUBSCRIBE:
        user_files = await user_repo.get_files_received(user.id) if user_repo else 5
        if user_files >= 5:
            missing = await subscription_service.get_missing_channels(client, user.id)
            if missing:
                keyboard = subscription_service.build_subscription_keyboard(missing, lang=lang)
                await message.reply_text(
                    tr("force_sub_prompt", lang, first_name=first_name),
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML,
                )
                return

    if settings.is_dual_bot:
        welcome_text = tr(
            "welcome_dual_text",
            lang,
            first_name=first_name,
            delivery_username=settings.DELIVERY_BOT_USERNAME,
        )
    else:
        welcome_text = tr("welcome_text", lang, first_name=first_name)

    start_kb = get_start_keyboard(
        support_url=settings.SUPPORT_GROUP_URL,
        backup_url=settings.BACKUP_CHANNEL_URL,
        lang=lang,
    )

    try:
        await message.reply_photo(
            photo=settings.START_IMAGE_URL,
            caption=welcome_text,
            reply_markup=start_kb,
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception as exc:
        logger.warning("Could not send start photo (fallback to text): %s", exc)
        await message.reply_text(welcome_text, reply_markup=start_kb, parse_mode=enums.ParseMode.HTML)
