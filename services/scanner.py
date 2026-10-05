# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional, Dict, Any, List

from pyrogram import Client, enums
from pyrogram.errors import FloodWait, MessageNotModified, RPCError
from pyrogram.types import InlineKeyboardMarkup, Message
from keyboards.inline import get_scanner_keyboard
from lang.manager import tr

from config import Settings
from services.manifest_manager import ManifestManager
from utils.logging import get_logger

logger = get_logger("services.scanner")

class ScanSession:

    def __init__(
        self,
        session_id: str,
        chat_id: int,
        start_id: int,
        end_id: int,
        status_message: Message,
    ):
        self.session_id = session_id
        self.chat_id = chat_id
        self.start_id = start_id
        self.end_id = end_id
        self.current_id = start_id
        self.files_found = 0
        self.files_since_last_edit = 0
        self.checked_in_batch = 0
        self.is_paused = False
        self.is_stopped = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self.status = "running"
        self.status_message = status_message
        self.started_at = time.time()
        self.last_edit_time = time.monotonic()
        self.task: Optional[asyncio.Task] = None
        self.group_captions: Dict[str, str] = {}

    def get_keyboard(self, finished: bool = False) -> Optional[InlineKeyboardMarkup]:
        if finished or self.is_stopped or self.status in ("completed", "stopped", "error"):
            return None
        return get_scanner_keyboard(
            session_id=self.session_id,
            paused=self.is_paused,
            resting=(self.status == "resting"),
        )

    def get_progress_text(self, note: str = "") -> str:
        total = max(1, self.end_id - self.start_id + 1)
        checked = max(0, min(total, self.current_id - self.start_id + 1))
        pct = (checked / total) * 100

        status_text = {
            "running": "⚡ Scanning",
            "paused": "⏸ Paused",
            "resting": "☕ Resting (2m Cooldown)",
            "stopped": "⏹ Stopped",
            "completed": "✅ Completed",
        }.get(self.status, self.status)

        base_text = tr(
            "admin_scan_progress_template",
            "en",
            checked=checked,
            total=total,
            pct=pct,
            saved=self.files_found,
            current_id=self.current_id,
            status=status_text,
        )
        if note:
            return f"{base_text}\n\n<i>{note}</i>"
        return base_text

    async def update_progress_message(
        self, bot: Client, note: str = "", finished: bool = False
    ) -> None:
        if not self.status_message:
            return

        text = self.get_progress_text(note=note)
        kb = self.get_keyboard(finished=finished)

        chat_id = self.status_message.chat.id
        msg_id = getattr(self.status_message, "id", None) or getattr(self.status_message, "message_id", None)

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=kb,
                parse_mode=enums.ParseMode.HTML,
            )
        except FloodWait as e:
            wait_sec = getattr(e, "value", None) or getattr(e, "x", 3)
            await asyncio.sleep(wait_sec + 1)
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception:
                pass
        except MessageNotModified:
            pass
        except Exception as exc:
            logger.debug("Non-fatal: error updating scan progress message: %s", exc)

    def pause(self) -> None:
        self.is_paused = True
        self.pause_event.clear()
        self.status = "paused"

    def resume(self) -> None:
        self.is_paused = False
        self.pause_event.set()
        self.status = "running"

    def stop(self) -> None:
        self.is_stopped = True
        self.pause_event.set()
        self.status = "stopped"

class ScannerService:

    def __init__(self, settings: Settings, manifest_manager: ManifestManager):
        self.settings = settings
        self.manifest_manager = manifest_manager
        self.active_sessions: Dict[int, ScanSession] = {}
        self.sessions_by_id: Dict[str, ScanSession] = {}

    def get_active_session(self, chat_id: int) -> Optional[ScanSession]:
        return self.active_sessions.get(chat_id)

    def get_session_by_id(self, session_id: str) -> Optional[ScanSession]:
        return self.sessions_by_id.get(session_id)

    async def start_scan(
        self,
        master_bot: Client,
        delivery_bot: Client,
        chat_id: int,
        start_id: int,
        end_id: int,
        status_message: Message,
        session_id: Optional[str] = None,
    ) -> ScanSession:
        sid = session_id or uuid.uuid4().hex[:8]
        start_clean = max(1, abs(start_id))
        end_clean = max(1, abs(end_id))
        actual_start = min(start_clean, end_clean)
        actual_end = max(start_clean, end_clean)
        session = ScanSession(
            session_id=sid,
            chat_id=chat_id,
            start_id=actual_start,
            end_id=actual_end,
            status_message=status_message,
        )

        self.active_sessions[chat_id] = session
        self.sessions_by_id[sid] = session

        task = asyncio.create_task(
            self._run_scan_loop(master_bot, delivery_bot, session),
            name=f"scan_{chat_id}_{sid}",
        )
        session.task = task
        return session

    async def _run_scan_loop(
        self,
        master_bot: Client,
        delivery_bot: Client,
        session: ScanSession,
    ) -> None:
        logger.info(
            "Starting MTProto scan for chat %d range %d-%d using Delivery Bot",
            session.chat_id,
            session.start_id,
            session.end_id,
        )

        fetch_bot = delivery_bot or master_bot
        batch_size = 180

        try:
            for chunk_start in range(session.start_id, session.end_id + 1, batch_size):
                if session.is_stopped:
                    break

                while session.is_paused:
                    await session.pause_event.wait()
                    if session.is_stopped:
                        break

                chunk_end = min(chunk_start + batch_size - 1, session.end_id)
                batch_ids = list(range(chunk_start, chunk_end + 1))

                msgs: List[Any] = []
                retries = 3
                while retries > 0:
                    try:
                        res = await fetch_bot.get_messages(chat_id=session.chat_id, message_ids=batch_ids)
                        msgs = res if isinstance(res, list) else [res]
                        break
                    except FloodWait as exc:
                        wait_sec = getattr(exc, "value", None) or getattr(exc, "x", 5)
                        logger.warning("FloodWait encountered in scanner: pausing %ds", wait_sec)
                        await session.update_progress_message(
                            master_bot,
                            note=f"⏳ FloodWait: Pausing {wait_sec}s for Telegram...",
                        )
                        await asyncio.sleep(wait_sec + 1)
                        retries -= 1
                    except Exception as exc:
                        logger.warning("Error fetching batch %d-%d: %s", chunk_start, chunk_end, exc)
                        break

                for m_item in msgs:
                    if not m_item:
                        continue
                    mgid = getattr(m_item, "media_group_id", None)
                    if mgid:
                        c_text = (getattr(m_item, "caption", None) or "").strip()
                        if c_text:
                            session.group_captions[str(mgid)] = c_text

                for msg in msgs:
                    if not msg or getattr(msg, "empty", False):
                        continue

                    msg_id = getattr(msg, "id", None) or getattr(msg, "message_id", None)
                    if msg_id:
                        session.current_id = msg_id

                    media = (
                        getattr(msg, "document", None)
                        or getattr(msg, "video", None)
                        or getattr(msg, "audio", None)
                        or getattr(msg, "animation", None)
                        or getattr(msg, "photo", None)
                    )
                    if media:
                        if getattr(msg, "document", None):
                            file_type = "document"
                        elif getattr(msg, "video", None):
                            file_type = "video"
                        elif getattr(msg, "audio", None):
                            file_type = "audio"
                        elif getattr(msg, "animation", None):
                            file_type = "animation"
                        elif getattr(msg, "photo", None):
                            file_type = "photo"
                        else:
                            file_type = "document"

                        file_name = getattr(media, "file_name", None) or getattr(media, "title", None)
                        if not file_name and file_type == "photo":
                            file_name = f"photo_{msg_id}.jpg"

                        mgid = getattr(msg, "media_group_id", None)
                        raw_cap = (getattr(msg, "caption", None) or "").strip()
                        if not raw_cap and mgid and str(mgid) in session.group_captions:
                            raw_cap = session.group_captions[str(mgid)]

                        caption = raw_cap if raw_cap else (file_name or f"file_{msg_id}")
                        file_size = getattr(media, "file_size", None)
                        mime_type = getattr(media, "mime_type", None) or ("image/jpeg" if file_type == "photo" else None)
                        file_id = getattr(media, "file_id", None)

                        await self.manifest_manager.ingest_file(
                            bot=master_bot,
                            caption=caption,
                            file_type=file_type,
                            file_id=file_id,
                            file_name=file_name,
                            file_size=file_size,
                            mime_type=mime_type,
                            source_chat_id=session.chat_id,
                            source_message_id=msg_id,
                            delivery_file_id=file_id,
                            debounce=True,
                        )
                        session.files_found += 1
                        session.files_since_last_edit += 1

                session.current_id = chunk_end
                session.checked_in_batch += len(batch_ids)

                if session.checked_in_batch >= 180:
                    session.status = "resting"
                    await session.update_progress_message(
                        master_bot,
                        note="⏸ Cooldown: Checked 180 messages. Resting for 2 minutes to protect bot...",
                    )
                    for _ in range(120):
                        if session.is_stopped:
                            break
                        while session.is_paused:
                            await session.pause_event.wait()
                            if session.is_stopped:
                                break
                        await asyncio.sleep(1)

                    if session.is_stopped:
                        break

                    session.checked_in_batch = 0
                    session.status = "running"
                    await session.update_progress_message(
                        master_bot,
                        note="▶ Cooldown ended. Resuming message scan...",
                    )

                now = time.monotonic()
                if (now - session.last_edit_time >= 1.5):
                    session.last_edit_time = now
                    session.files_since_last_edit = 0
                    await session.update_progress_message(master_bot)

                await asyncio.sleep(0.05)

        except Exception as exc:
            logger.exception("Unexpected error in scan loop: %s", exc)
            session.status = "error"
            await session.update_progress_message(
                master_bot, note=f"❌ Error occurred: {exc}", finished=True
            )
        finally:
            if session.is_stopped:
                session.status = "stopped"
                finish_note = f"⏹ Stopped by owner. Saved {session.files_found} files."
            elif session.status != "error":
                session.status = "completed"
                finish_note = f"✅ Completed! Saved {session.files_found} files."
            else:
                finish_note = "❌ Terminated with error."

            await session.update_progress_message(
                master_bot, note=finish_note, finished=True
            )

            if session.files_found > 0:
                try:
                    logger.info("Scan completed with %d files. Flushing manifest...", session.files_found)
                    await self.manifest_manager.flush_manifest(master_bot, force=True)
                except Exception as exc:
                    logger.exception("Failed to flush manifest after scan: %s", exc)

            self.active_sessions.pop(session.chat_id, None)
            self.sessions_by_id.pop(session.session_id, None)
