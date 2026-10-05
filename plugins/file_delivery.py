# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Optional, Any
from pyrogram import Client, enums
from pyrogram.types import Message

from config import Settings
from keyboards.inline import get_redirect_to_master_keyboard
from lang.manager import tr
from services.file_delivery import FileDeliveryService
from utils.exceptions import UserBlockedError
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.file_delivery")

async def handle_delivery_start_command(
    client: Client,
    message: Message,
    settings: Settings,
    file_delivery_service: FileDeliveryService,
    subscription_service: Optional[Any] = None,
    user_repo: Optional[Any] = None,
    master_bot: Optional[Client] = None,
    lang: str = "en",
) -> None:
    user = message.from_user
    if not user:
        return

    tokens = (message.text or "").strip().split(maxsplit=1)
    token = tokens[1].strip() if len(tokens) > 1 else None
    first_name = escape_html(user.first_name or "Friend")

    if token:
        if not settings.is_owner(user.id) and user_repo and subscription_service and settings.SUBSCRIBE:
            user_files = await user_repo.get_files_received(user.id)
            if user_files >= 5:
                check_bot = master_bot or client
                missing = await subscription_service.get_missing_channels(check_bot, user.id)
                if missing:
                    keyboard = subscription_service.build_subscription_keyboard(missing, lang=lang)
                    await message.reply_text(
                        tr("force_sub_prompt", lang, first_name=first_name),
                        reply_markup=keyboard,
                        parse_mode=enums.ParseMode.HTML,
                    )
                    return
        if token.startswith("random"):
            parts = token.split("_")
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            await file_delivery_service.deliver_random_files(client, user.id, count=count, lang=lang)
            return

        try:
            success, msg = await file_delivery_service.deliver_file_by_token(
                bot=client,
                user_id=user.id,
                token=token,
                lang=lang,
            )
            if not success:
                await message.reply_text(
                    f"⚠️ {msg}",
                    reply_markup=get_redirect_to_master_keyboard(settings.MASTER_BOT_USERNAME, lang=lang),
                    parse_mode=enums.ParseMode.HTML,
                )
        except UserBlockedError:
            await message.reply_text(tr("user_blocked", lang), parse_mode=enums.ParseMode.HTML)
        except Exception as exc:
            logger.exception("Unexpected error processing token %s: %s", token[:8], exc)
            await message.reply_text(
                tr("internal_error", lang),
                reply_markup=get_redirect_to_master_keyboard(settings.MASTER_BOT_USERNAME, lang=lang),
                parse_mode=enums.ParseMode.HTML,
            )
        return

    welcome_text = tr(
        "delivery_agent_welcome",
        lang,
        first_name=first_name,
        master_username=settings.MASTER_BOT_USERNAME,
    )
    await message.reply_text(
        welcome_text,
        reply_markup=get_redirect_to_master_keyboard(settings.MASTER_BOT_USERNAME, lang=lang),
        parse_mode=enums.ParseMode.HTML,
    )

async def handle_random_command(
    client: Client,
    message: Message,
    settings: Settings,
    file_delivery_service: FileDeliveryService,
    subscription_service: Optional[Any] = None,
    user_repo: Optional[Any] = None,
    master_bot: Optional[Client] = None,
    lang: str = "en",
) -> None:
    user = message.from_user
    if not user:
        return

    first_name = escape_html(user.first_name or "Friend")
    if not settings.is_owner(user.id) and user_repo and subscription_service and settings.SUBSCRIBE:
        user_files = await user_repo.get_files_received(user.id)
        if user_files >= 5:
            check_bot = master_bot or client
            missing = await subscription_service.get_missing_channels(check_bot, user.id)
            if missing:
                keyboard = subscription_service.build_subscription_keyboard(missing, lang=lang)
                await message.reply_text(
                    tr("force_sub_prompt", lang, first_name=first_name),
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML,
                )
                return

    text_parts = (message.text or "").strip().split(maxsplit=1)
    raw_count = text_parts[1].strip() if len(text_parts) > 1 else "1"
    count = int(raw_count) if raw_count.isdigit() else 1
    count = max(1, min(10, count))

    delivered_count, reply_msg = await file_delivery_service.deliver_random_files(
        bot=client,
        user_id=user.id,
        count=count,
        lang=lang,
    )
    if delivered_count == 0:
        await message.reply_text(reply_msg, parse_mode=enums.ParseMode.HTML)

async def handle_delivery_plain_text(client: Client, message: Message, settings: Settings, lang: str = "en") -> None:
    await message.reply_text(
        tr("delivery_plain_text", lang, master_username=settings.MASTER_BOT_USERNAME),
        reply_markup=get_redirect_to_master_keyboard(settings.MASTER_BOT_USERNAME, lang=lang),
        parse_mode=enums.ParseMode.HTML,
    )
