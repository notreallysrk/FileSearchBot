# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
import math
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Settings
from lang.manager import tr
from services.cache_manager import TTLCache
from services.file_tokens import FileTokenService
from utils.formatting import format_result_button_text
from utils.logging import get_logger

logger = get_logger("keyboards.pagination")

@dataclass
class SearchSession:
    session_id: str
    user_id: int
    query: str
    file_ids: List[str]
    all_file_ids: List[str] = field(default_factory=list)
    current_filter: Optional[str] = None
    page_size: int = 10

    def __post_init__(self):
        if not self.all_file_ids:
            self.all_file_ids = list(self.file_ids)

    @property
    def total_items(self) -> int:
        return len(self.file_ids)

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(len(self.file_ids) / self.page_size))

    def get_page_file_ids(self, page: int) -> List[str]:
        if page < 1 or page > self.total_pages:
            return []
        start = (page - 1) * self.page_size
        end = start + self.page_size
        return self.file_ids[start:end]

    def apply_filter(self, media_type: Optional[str], search_engine: Any) -> None:
        if not media_type or media_type.lower() in ("all", "none", "*"):
            self.current_filter = None
            self.file_ids = list(self.all_file_ids)
            return

        mtype = media_type.lower()
        self.current_filter = mtype
        filtered: List[str] = []
        for fid in self.all_file_ids:
            rec = search_engine.get_file(fid)
            if not rec:
                continue
            rec_type = (rec.file_type or "document").lower()
            if mtype == "video" and rec_type in ("video", "animation"):
                filtered.append(fid)
            elif mtype == "document" and rec_type in ("document",):
                filtered.append(fid)
            elif mtype == "photo" and rec_type in ("photo", "image"):
                filtered.append(fid)
            elif mtype == "audio" and rec_type in ("audio", "voice"):
                filtered.append(fid)
            elif rec_type == mtype:
                filtered.append(fid)
        self.file_ids = filtered

class PaginationManager:
    def __init__(self, settings: Settings, token_service: FileTokenService, cache_size: int = 2000):
        self.settings = settings
        self.token_service = token_service
        self._sessions: TTLCache[SearchSession] = TTLCache(maxsize=cache_size, default_ttl=600.0)

    def create_session(self, user_id: int, query: str, file_ids: List[str]) -> SearchSession:
        session_id = uuid.uuid4().hex[:8]
        session = SearchSession(
            session_id=session_id,
            user_id=user_id,
            query=query,
            file_ids=list(file_ids),
            all_file_ids=list(file_ids),
            page_size=self.settings.SEARCH_PAGE_SIZE,
        )
        self._sessions.set(session_id, session)
        return session

    def get_session(self, session_id: str) -> Optional[SearchSession]:
        return self._sessions.get(session_id)

    async def build_search_keyboard(
        self,
        session: SearchSession,
        page: int,
        search_engine: Any,
        lang: str = "en",
    ) -> InlineKeyboardMarkup:
        page_file_ids = session.get_page_file_ids(page)
        buttons: List[List[InlineKeyboardButton]] = []

        for fid in page_file_ids:
            file_record = search_engine.get_file(fid)
            if not file_record:
                continue

            caption = file_record.caption or file_record.file_name or "File"
            size = file_record.file_size
            btn_title = format_result_button_text(caption, size, max_length=42)

            token = await self.token_service.create_token(fid)
            deep_link = f"https://t.me/{self.settings.delivery_username}?start={token}"
            buttons.append([InlineKeyboardButton(text=btn_title, url=deep_link, style="success")])

        counts = {"video": 0, "document": 0, "photo": 0, "audio": 0}
        for fid in session.all_file_ids:
            rec = search_engine.get_file(fid)
            if not rec:
                continue
            t = (rec.file_type or "document").lower()
            if t in ("video", "animation"):
                counts["video"] += 1
            elif t == "document":
                counts["document"] += 1
            elif t in ("photo", "image"):
                counts["photo"] += 1
            elif t in ("audio", "voice"):
                counts["audio"] += 1

        filter_row: List[InlineKeyboardButton] = []
        if counts["video"] > 0:
            label = f"🎬 ({counts['video']})"
            v_style = "danger" if session.current_filter == "video" else "default"
            filter_row.append(InlineKeyboardButton(text=label, callback_data=f"flt:{session.session_id}:video", style=v_style))
        if counts["document"] > 0:
            label = f"📃 ({counts['document']})"
            d_style = "danger" if session.current_filter == "document" else "default"
            filter_row.append(InlineKeyboardButton(text=label, callback_data=f"flt:{session.session_id}:document", style=d_style))
        if counts["photo"] > 0:
            label = f"📷 ({counts['photo']})"
            p_style = "danger" if session.current_filter == "photo" else "default"
            filter_row.append(InlineKeyboardButton(text=label, callback_data=f"flt:{session.session_id}:photo", style=p_style))
        if counts["audio"] > 0:
            label = f"🎵 ({counts['audio']})"
            a_style = "danger" if session.current_filter == "audio" else "default"
            filter_row.append(InlineKeyboardButton(text=label, callback_data=f"flt:{session.session_id}:audio", style=a_style))

        if session.current_filter:
            filter_row.append(InlineKeyboardButton(text=f"🌐 All ({len(session.all_file_ids)})", callback_data=f"flt:{session.session_id}:all", style="default"))

        if filter_row:
            buttons.append(filter_row)

        total_pages = session.total_pages
        if total_pages > 1:
            nav_row: List[InlineKeyboardButton] = []
            if page > 1:
                nav_row.append(
                    InlineKeyboardButton(
                        text=tr("btn_prev", lang),
                        callback_data=f"sp:{session.session_id}:{page - 1}",
                        style="primary",
                    )
                )
            nav_row.append(
                InlineKeyboardButton(
                    text=f"📄 {page}/{total_pages}",
                    callback_data="noop",
                    style="default",
                )
            )
            if page < total_pages:
                nav_row.append(
                    InlineKeyboardButton(
                        text=tr("btn_next", lang),
                        callback_data=f"sp:{session.session_id}:{page + 1}",
                        style="primary",
                    )
                )
            buttons.append(nav_row)

        return InlineKeyboardMarkup(buttons)
