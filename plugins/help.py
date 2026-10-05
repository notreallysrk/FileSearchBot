# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Optional
from pyrogram import Client, enums
from pyrogram.types import Message, CallbackQuery

from config import Settings
from keyboards.inline import get_start_keyboard, get_help_keyboard
from lang.manager import tr
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.help")

def get_help_caption(user_id: int, settings: Settings, lang: str = "en") -> str:
    if settings.is_owner(user_id):
        return tr("help_text_owner", lang)
    return tr("help_text", lang)

async def handle_help_command(
    client: Client,
    message: Message,
    settings: Settings,
    lang: str = "en",
) -> None:
    user = message.from_user
    user_id = user.id if user else 0
    help_caption = get_help_caption(user_id, settings, lang)
    support_url = settings.SUPPORT_GROUP_URL or settings.BACKUP_CHANNEL_URL or ""
    help_kb = get_help_keyboard(support_url=support_url, from_start=False, lang=lang)

    if len(help_caption) <= 1024:
        try:
            await message.reply_photo(
                photo=settings.START_IMAGE_URL,
                caption=help_caption,
                reply_markup=help_kb,
                parse_mode=enums.ParseMode.HTML,
            )
            return
        except Exception as exc:
            logger.warning("Could not send help photo (fallback to text): %s", exc)

    await message.reply_text(help_caption, reply_markup=help_kb, parse_mode=enums.ParseMode.HTML)

async def handle_help_callback(
    client: Client,
    query: CallbackQuery,
    settings: Settings,
    lang: str = "en",
) -> None:
    user = query.from_user
    user_id = user.id if user else 0
    help_caption = get_help_caption(user_id, settings, lang)
    support_url = settings.SUPPORT_GROUP_URL or settings.BACKUP_CHANNEL_URL or ""
    help_kb = get_help_keyboard(support_url=support_url, from_start=True, lang=lang)

    if query.message:
        if getattr(query.message, "photo", None):
            try:
                await query.edit_message_caption(
                    caption=help_caption,
                    reply_markup=help_kb,
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception as exc:
                logger.error("Failed to edit caption to help: %s", exc)
        else:
            try:
                await query.edit_message_text(
                    text=help_caption,
                    reply_markup=help_kb,
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception as exc:
                logger.error("Failed to edit text to help: %s", exc)

    await query.answer()

async def handle_start_menu_callback(
    client: Client,
    query: CallbackQuery,
    settings: Settings,
    lang: str = "en",
) -> None:
    user = query.from_user
    first_name = escape_html(user.first_name if user else "Friend")

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

    if query.message:
        if getattr(query.message, "photo", None):
            try:
                await query.edit_message_caption(
                    caption=welcome_text,
                    reply_markup=start_kb,
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception as exc:
                logger.error("Failed to edit caption to start: %s", exc)
        else:
            try:
                await query.edit_message_text(
                    text=welcome_text,
                    reply_markup=start_kb,
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception as exc:
                logger.error("Failed to edit text to start: %s", exc)

    await query.answer()
