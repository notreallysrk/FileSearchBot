# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import asyncio
import re
from typing import Optional
from pyrogram import Client, enums
from pyrogram.types import Message

from config import settings
from keyboards.inline import get_empty_search_keyboard
from keyboards.pagination import PaginationManager
from lang.manager import tr
from services.cache_manager import TTLCache
from services.manifest_manager import ManifestManager
from services.search_engine import SearchEngine
from services.statistics_manager import StatisticsManager
from services.request_manager import RequestManager
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.search")
_ALBUM_CAPTIONS: TTLCache[str] = TTLCache(maxsize=1000, default_ttl=3600.0)

async def _safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception as exc:
        msg_id = getattr(message, "id", None) or getattr(message, "message_id", 0)
        logger.debug("Non-fatal: could not delete query message %s: %s", msg_id, exc)

async def handle_storage_file_received(
    client: Client,
    message: Message,
    manifest_manager: ManifestManager,
    stats_manager: StatisticsManager,
) -> None:
    file_id = None
    file_type = "document"
    file_name = None
    file_size = None
    mime_type = None

    msg_id = getattr(message, "id", None) or getattr(message, "message_id", 0)

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
        file_size = message.document.file_size
        mime_type = message.document.mime_type
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.video.file_name
        file_size = message.video.file_size
        mime_type = message.video.mime_type
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
        file_name = message.audio.file_name or message.audio.title or f"audio_{msg_id}.mp3"
        file_size = message.audio.file_size
        mime_type = message.audio.mime_type
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "animation"
        file_name = message.animation.file_name
        file_size = message.animation.file_size
        mime_type = message.animation.mime_type
    elif message.photo:
        file_id = message.photo.file_id
        file_type = "photo"
        file_name = f"photo_{msg_id}.jpg"
        file_size = message.photo.file_size
        mime_type = "image/jpeg"
    else:
        return

    mgid = getattr(message, "media_group_id", None)
    raw_cap = (message.caption or "").strip()
    if mgid:
        if raw_cap:
            _ALBUM_CAPTIONS.set(str(mgid), raw_cap)
        else:
            cached_cap = _ALBUM_CAPTIONS.get(str(mgid))
            if cached_cap:
                raw_cap = cached_cap
            else:
                await asyncio.sleep(0.8)
                cached_cap = _ALBUM_CAPTIONS.get(str(mgid))
                if cached_cap:
                    raw_cap = cached_cap

    caption = raw_cap or file_name or f"file_{msg_id}"

    try:
        record = await manifest_manager.ingest_file(
            bot=client,
            caption=caption,
            file_type=file_type,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            source_chat_id=message.chat.id,
            source_message_id=msg_id,
        )
        logger.info("Indexed file: %s (caption='%s')", record["id"], caption[:30])
    except Exception as exc:
        logger.exception("Failed to ingest file msg %d: %s", msg_id, exc)

async def handle_user_search(
    client: Client,
    message: Message,
    search_engine: SearchEngine,
    pagination_manager: PaginationManager,
    stats_manager: StatisticsManager,
    request_manager: Optional[RequestManager] = None,
    lang: str = "en",
    override_query: Optional[str] = None,
) -> None:
    query = (override_query or message.text or "").strip()
    user = message.from_user
    if not user:
        return

    if not override_query and query.startswith("/"):
        return

    if message.chat.type == enums.ChatType.PRIVATE:
        asyncio.create_task(_safe_delete_message(message))

    if "#request" in query.lower():
        clean_desc = re.sub(r"#request\b", "", query, flags=re.IGNORECASE).strip()
        if len(clean_desc) < 3:
            await message.reply_text(tr("request_too_short", lang), parse_mode=enums.ParseMode.HTML)
            return
        if len(clean_desc) > 300:
            await message.reply_text(tr("request_too_long", lang), parse_mode=enums.ParseMode.HTML)
            return

        if request_manager:
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
                logger.exception("Failed to submit #request for %d: %s", user.id, exc)
                await message.reply_text(tr("internal_error", lang), parse_mode=enums.ParseMode.HTML)
        return

    if len(query) < 2:
        await message.reply_text(tr("search_too_short", lang), parse_mode=enums.ParseMode.HTML)
        return

    if len(query) > 100:
        await message.reply_text(tr("search_too_long", lang), parse_mode=enums.ParseMode.HTML)
        return

    stats_manager.record_search()
    results = search_engine.search(query=query, limit=100)
    clean_query = escape_html(query)

    if not results:
        await message.reply_text(
            tr("search_no_results", lang, query=clean_query),
            reply_markup=get_empty_search_keyboard(lang=lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    file_ids = [f.id for f in results]
    session = pagination_manager.create_session(user_id=user.id, query=query, file_ids=file_ids)
    keyboard = await pagination_manager.build_search_keyboard(
        session, page=1, search_engine=search_engine, lang=lang
    )

    total = session.total_items
    pages = session.total_pages

    await message.reply_text(
        tr("search_results_header", lang, query=clean_query, total=total, page=1, pages=pages),
        reply_markup=keyboard,
        parse_mode=enums.ParseMode.HTML,
    )


async def handle_search_query(
    client: Client,
    message: Message,
    search_engine: SearchEngine,
    pagination_manager: PaginationManager,
    stats_manager: StatisticsManager,
    request_manager: Optional[RequestManager] = None,
    lang: str = "en",
    query: Optional[str] = None,
    **kwargs,
) -> None:
    await handle_user_search(
        client=client,
        message=message,
        search_engine=search_engine,
        pagination_manager=pagination_manager,
        stats_manager=stats_manager,
        request_manager=request_manager,
        lang=lang,
        override_query=query,
    )


async def handle_explore_command(
    client: Client,
    message: Message,
    search_engine: SearchEngine,
    pagination_manager: PaginationManager,
    lang: str = "en",
) -> None:
    user = message.from_user
    if not user:
        return
    all_files = search_engine.get_all_files()[:100]
    if not all_files:
        await message.reply_text(tr("search_no_results", lang, query="Explore"), parse_mode=enums.ParseMode.HTML)
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
    await message.reply_text(text, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
