# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import re
from typing import Optional, Set, Dict
from pyrogram import Client, enums
from pyrogram.enums import ChatType
from pyrogram.types import Message

from lang.manager import tr
from services.request_manager import RequestManager
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.request")

ACTIVE_REQUEST_USERS: Set[int] = set()
ACTIVE_GROUP_REQUESTS: Dict[int, int] = {}

def is_user_requesting(user_id: int) -> bool:
    return user_id in ACTIVE_REQUEST_USERS

def is_group_requesting(chat_id: int, user_id: int) -> bool:
    return ACTIVE_GROUP_REQUESTS.get(chat_id) == user_id

def clear_user_request(user_id: int) -> None:
    ACTIVE_REQUEST_USERS.discard(user_id)

def clear_group_request(chat_id: int) -> None:
    ACTIVE_GROUP_REQUESTS.pop(chat_id, None)

async def handle_cancel_command(client: Client, message: Message, lang: str = "en") -> None:
    user = message.from_user
    if not user:
        return

    is_active = False
    if message.chat.type == ChatType.PRIVATE:
        if user.id in ACTIVE_REQUEST_USERS:
            ACTIVE_REQUEST_USERS.discard(user.id)
            is_active = True
    else:
        if ACTIVE_GROUP_REQUESTS.get(message.chat.id) == user.id:
            ACTIVE_GROUP_REQUESTS.pop(message.chat.id, None)
            is_active = True

    if not is_active:
        await message.reply_text(tr("request_cancel_no_active", lang), parse_mode=enums.ParseMode.HTML)
        return

    await message.reply_text(tr("request_cancelled", lang), parse_mode=enums.ParseMode.HTML)

async def handle_request_command(
    client: Client,
    message: Message,
    request_manager: Optional[RequestManager] = None,
    lang: str = "en",
) -> None:
    user = message.from_user
    if not user:
        return

    text_parts = (message.text or "").strip().split(maxsplit=1)
    description = text_parts[1].strip() if len(text_parts) > 1 else ""

    if description:
        if len(description) < 3:
            await message.reply_text(tr("request_too_short", lang), parse_mode=enums.ParseMode.HTML)
            return
        if len(description) > 300:
            await message.reply_text(tr("request_too_long", lang), parse_mode=enums.ParseMode.HTML)
            return

        if request_manager:
            try:
                doc = await request_manager.submit_request(
                    bot=client,
                    user_id=user.id,
                    description=description,
                    first_name=user.first_name,
                    username=user.username,
                )
                await message.reply_text(
                    tr(
                        "request_submitted",
                        lang,
                        description=escape_html(description),
                        request_id=doc["_id"],
                    ),
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception as exc:
                logger.exception("Failed to submit request for user %d: %s", user.id, exc)
                await message.reply_text(tr("internal_error", lang), parse_mode=enums.ParseMode.HTML)
        return

    first_name = escape_html(user.first_name or "Friend")
    if message.chat.type == ChatType.PRIVATE:
        ACTIVE_REQUEST_USERS.add(user.id)
        await message.reply_text(tr("request_prompt", lang), parse_mode=enums.ParseMode.HTML)
    else:
        ACTIVE_GROUP_REQUESTS[message.chat.id] = user.id
        prompt_text = (
            "📝 <b>Request File</b>\n\n"
            f"👤 {first_name}\n"
            "Please send the title of the file you want to request.\n"
            "Or use /cancel to abort."
        )
        await message.reply_text(prompt_text, parse_mode=enums.ParseMode.HTML)

async def handle_request_description_received(
    client: Client,
    message: Message,
    request_manager: RequestManager,
    lang: str = "en",
) -> bool:
    user = message.from_user
    if not user or user.id not in ACTIVE_REQUEST_USERS:
        return False

    text = (message.text or "").strip()
    if text.startswith("/"):
        if text.startswith("/cancel"):
            ACTIVE_REQUEST_USERS.discard(user.id)
            await message.reply_text(tr("request_cancelled", lang), parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text(tr("request_text_only", lang), parse_mode=enums.ParseMode.HTML)
        return True

    if len(text) < 3:
        await message.reply_text(tr("request_too_short", lang), parse_mode=enums.ParseMode.HTML)
        return True

    if len(text) > 300:
        await message.reply_text(tr("request_too_long", lang), parse_mode=enums.ParseMode.HTML)
        return True

    ACTIVE_REQUEST_USERS.discard(user.id)
    clean_text = escape_html(text)

    try:
        doc = await request_manager.submit_request(
            bot=client,
            user_id=user.id,
            description=text,
            first_name=user.first_name,
            username=user.username,
        )
        await message.reply_text(
            tr(
                "request_submitted",
                lang,
                description=clean_text,
                request_id=doc["_id"],
            ),
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Failed to submit request for user %d: %s", user.id, exc)
        await message.reply_text(tr("internal_error", lang), parse_mode=enums.ParseMode.HTML)

    return True

async def handle_group_request_description_received(
    client: Client,
    message: Message,
    request_manager: RequestManager,
    lang: str = "en",
) -> bool:
    user = message.from_user
    if not user or ACTIVE_GROUP_REQUESTS.get(message.chat.id) != user.id:
        return False

    text = (message.text or "").strip()
    if text.startswith("/"):
        if text.startswith("/cancel"):
            ACTIVE_GROUP_REQUESTS.pop(message.chat.id, None)
            await message.reply_text(tr("request_cancelled", lang), parse_mode=enums.ParseMode.HTML)
            return True
        return False

    if len(text) < 3:
        await message.reply_text(tr("request_too_short", lang), parse_mode=enums.ParseMode.HTML)
        return True

    if len(text) > 300:
        await message.reply_text(tr("request_too_long", lang), parse_mode=enums.ParseMode.HTML)
        return True

    ACTIVE_GROUP_REQUESTS.pop(message.chat.id, None)
    clean_text = escape_html(text)

    try:
        doc = await request_manager.submit_request(
            bot=client,
            user_id=user.id,
            description=text,
            first_name=user.first_name,
            username=user.username,
        )
        await message.reply_text(
            tr(
                "request_submitted",
                lang,
                description=clean_text,
                request_id=doc["_id"],
            ),
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Failed to submit group request for user %d: %s", user.id, exc)
        await message.reply_text(tr("internal_error", lang), parse_mode=enums.ParseMode.HTML)

    return True

async def handle_hashtag_request(
    client: Client,
    message: Message,
    request_manager: RequestManager,
    lang: str = "en",
) -> bool:
    user = message.from_user
    if not user:
        return False

    text = (message.text or "").strip()
    clean_desc = re.sub(r"#request\b", "", text, flags=re.IGNORECASE).strip()

    if not clean_desc:
        if message.chat.type == ChatType.PRIVATE:
            ACTIVE_REQUEST_USERS.add(user.id)
            await message.reply_text(tr("request_prompt", lang), parse_mode=enums.ParseMode.HTML)
        else:
            ACTIVE_GROUP_REQUESTS[message.chat.id] = user.id
            first_name = escape_html(user.first_name or "Friend")
            prompt_text = (
                "📝 <b>Request File</b>\n\n"
                f"👤 {first_name}\n"
                "Please send the title of the file you want to request.\n"
                "Or use /cancel to abort."
            )
            await message.reply_text(prompt_text, parse_mode=enums.ParseMode.HTML)
        return True

    if len(clean_desc) < 3:
        await message.reply_text(tr("request_too_short", lang), parse_mode=enums.ParseMode.HTML)
        return True

    if len(clean_desc) > 300:
        await message.reply_text(tr("request_too_long", lang), parse_mode=enums.ParseMode.HTML)
        return True

    try:
        doc = await request_manager.submit_request(
            bot=client,
            user_id=user.id,
            description=clean_desc,
            first_name=user.first_name,
            username=user.username,
        )
        await message.reply_text(
            tr(
                "request_submitted",
                lang,
                description=escape_html(clean_desc),
                request_id=doc["_id"],
            ),
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Failed to submit #request for user %d: %s", user.id, exc)
        await message.reply_text(tr("internal_error", lang), parse_mode=enums.ParseMode.HTML)

    return True
