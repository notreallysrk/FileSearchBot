# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import orjson

    def _dumps_json(obj: Any) -> bytes:
        return orjson.dumps(obj, option=orjson.OPT_INDENT_2)

    def _loads_json(data: bytes | str) -> Any:
        return orjson.loads(data)
except ImportError:
    import json

    def _dumps_json(obj: Any) -> bytes:
        return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")

    def _loads_json(data: bytes | str) -> Any:
        return json.loads(data)

from pyrogram import Client, enums

from config import Settings
from database.manifest import ManifestRepository
from services.search_engine import SearchEngine
from utils.exceptions import ManifestError, ManifestCorruptError, ManifestUploadError
from utils.logging import get_logger

logger = get_logger("manifest_manager")

class ManifestManager:

    def __init__(
        self,
        settings: Settings,
        manifest_repo: ManifestRepository,
        search_engine: SearchEngine,
    ):
        self.settings = settings
        self.manifest_repo = manifest_repo
        self.search_engine = search_engine

        self._lock = asyncio.Lock()

        self._version: int = 1
        self._updated_at: str = datetime.now(timezone.utc).isoformat()
        self._files_map: Dict[str, Dict[str, Any]] = {}
        self._source_keys: set[str] = set()

        self._dirty: bool = False
        self._pending_files_count: int = 0
        self._debounce_task: Optional[asyncio.Task] = None
        self._debounce_seconds: float = getattr(settings, "MANIFEST_DEBOUNCE_MINUTES", 30) * 60
        self._bot_for_flush: Optional[Client] = None

    @property
    def version(self) -> int:
        return self._version

    @property
    def files_count(self) -> int:
        return len(self._files_map)

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def pending_uncommitted_count(self) -> int:
        return self._pending_files_count

    @property
    def updated_at(self) -> str:
        return self._updated_at

    def is_source_indexed(self, chat_id: int, message_id: int) -> bool:
        key = f"{chat_id}:{message_id}"
        return key in self._source_keys

    async def initialize_and_load(self, bot: Client) -> None:
        async with self._lock:
            self._bot_for_flush = bot
            pointer = await self.manifest_repo.get_pointer()
            if not pointer:
                logger.warning("No manifest pointer found in MongoDB. Initializing fresh empty manifest.")
                self._version = 1
                self._updated_at = datetime.now(timezone.utc).isoformat()
                self._files_map = {}
                self._source_keys = set()
                self.search_engine.build_index([], version=1)
                return

            file_id = pointer.get("file_id")
            version = pointer.get("version", 1)
            logger.info("Loading manifest from Telegram: file_id=%s, version=%d", file_id[:12] if file_id else "N/A", version)

            try:
                tg_file = await bot.download_media(file_id, in_memory=True)
                if hasattr(tg_file, "getbuffer"):
                    raw_bytes = bytes(tg_file.getbuffer())
                elif isinstance(tg_file, (str, Path)):
                    with open(tg_file, "rb") as f:
                        raw_bytes = f.read()
                    try:
                        os.remove(tg_file)
                    except OSError:
                        pass
                else:
                    raw_bytes = bytes(tg_file)
                data = _loads_json(raw_bytes)

                self._load_from_dict(data, expected_version=version)
                logger.info(
                    "Successfully recovered manifest v%d with %d files",
                    self._version,
                    len(self._files_map),
                )
            except Exception as exc:
                logger.exception("Failed to load Telegram manifest: %s", exc)
                raise ManifestError(f"Startup recovery failed to download manifest: {exc}") from exc

    def _load_from_dict(self, data: Dict[str, Any], expected_version: Optional[int] = None) -> None:
        if not isinstance(data, dict) or "files" not in data:
            raise ManifestCorruptError("Manifest root must be an object with a 'files' array.")

        self._version = data.get("version", expected_version or 1)
        self._updated_at = data.get("updated_at", datetime.now(timezone.utc).isoformat())

        files_list = data.get("files", [])
        new_map: Dict[str, Dict[str, Any]] = {}
        new_source_keys: set[str] = set()

        for item in files_list:
            if not isinstance(item, dict):
                continue
            fid = item.get("id")
            if not fid:
                continue
            new_map[fid] = item

            chat_id = item.get("source_chat_id")
            msg_id = item.get("source_message_id")
            if chat_id is not None and msg_id is not None:
                new_source_keys.add(f"{chat_id}:{msg_id}")

        self._files_map = new_map
        self._source_keys = new_source_keys
        self.search_engine.build_index(list(self._files_map.values()), version=self._version)

    async def ingest_file(
        self,
        bot: Client,
        caption: str,
        file_type: str,
        file_id: str,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        source_chat_id: Optional[int] = None,
        source_message_id: Optional[int] = None,
        delivery_file_id: Optional[str] = None,
        debounce: bool = True,
    ) -> Dict[str, Any]:
        async with self._lock:
            self._bot_for_flush = bot

            if source_chat_id and source_message_id:
                source_key = f"{source_chat_id}:{source_message_id}"
                if source_key in self._source_keys:
                    logger.warning("File already indexed from source: %s", source_key)
                    for f in self._files_map.values():
                        if f.get("source_chat_id") == source_chat_id and f.get("source_message_id") == source_message_id:
                            return f

            internal_id = uuid.uuid4().hex[:16]
            now_iso = datetime.now(timezone.utc).isoformat()

            file_record = {
                "id": internal_id,
                "caption": caption.strip(),
                "file_type": file_type,
                "file_id": file_id,
                "delivery_file_id": delivery_file_id or file_id,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "source_chat_id": source_chat_id,
                "source_message_id": source_message_id,
                "created_at": now_iso,
            }

            self._files_map[internal_id] = file_record
            if source_chat_id and source_message_id:
                self._source_keys.add(f"{source_chat_id}:{source_message_id}")

            self._dirty = True
            self._pending_files_count += 1
            self.search_engine.build_index(list(self._files_map.values()), version=self._version)
            logger.info("Ingested file in memory: id=%s (pending: %d)", internal_id, self._pending_files_count)

        if debounce:
            self._schedule_debounce(bot)
        else:
            await self.flush_manifest(bot, force=True)

        return file_record

    def _schedule_debounce(self, bot: Client) -> None:
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        async def _debounce_timer():
            try:
                await asyncio.sleep(self._debounce_seconds)
                logger.info(
                    "Debounce window (%ds) elapsed without new files. Flushing manifest to Telegram...",
                    int(self._debounce_seconds),
                )
                await self.flush_manifest(bot)
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.exception("Error during scheduled manifest flush: %s", exc)

        self._debounce_task = asyncio.create_task(_debounce_timer())

    async def flush_manifest(self, bot: Optional[Client] = None, force: bool = False) -> bool:
        target_bot = bot or self._bot_for_flush
        if not target_bot:
            logger.warning("Cannot flush manifest: no bot instance available.")
            return False

        async with self._lock:
            if not self._dirty and not force:
                return False

            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()

            new_version = self._version + 1
            now_iso = datetime.now(timezone.utc).isoformat()

            manifest_dict = {
                "version": new_version,
                "updated_at": now_iso,
                "files": list(self._files_map.values()),
            }

            uploaded_msg = await self._upload_manifest_document(target_bot, manifest_dict, new_version)
            if not uploaded_msg or not uploaded_msg.document:
                raise ManifestUploadError("Failed to upload db.json document to Telegram logger group.")

            new_tg_file_id = uploaded_msg.document.file_id

            await self.manifest_repo.update_pointer(
                chat_id=self.settings.LOGGER_GROUP_ID,
                message_id=uploaded_msg.id,
                file_id=new_tg_file_id,
                version=new_version,
            )

            self._version = new_version
            self._updated_at = now_iso
            self._dirty = False
            flushed_count = self._pending_files_count
            self._pending_files_count = 0

            self.search_engine.build_index(list(self._files_map.values()), version=new_version)
            logger.info(
                "Successfully flushed manifest to Telegram: version=%d (%d total files, %d new)",
                new_version,
                len(self._files_map),
                flushed_count,
            )
            return True

    async def get_manifest_info(self) -> Dict[str, Any]:
        pointer = await self.manifest_repo.get_pointer()
        chat_id = pointer.get("chat_id") if pointer else None
        msg_id = pointer.get("message_id") if pointer else None
        msg_url = None
        if chat_id and msg_id:
            clean_cid = str(chat_id)
            if clean_cid.startswith("-100"):
                clean_cid = clean_cid[4:]
            elif clean_cid.startswith("-"):
                clean_cid = clean_cid[1:]
            msg_url = f"https://t.me/c/{clean_cid}/{msg_id}"

        return {
            "version": self._version,
            "files_count": len(self._files_map),
            "pending_count": self._pending_files_count,
            "is_dirty": self._dirty,
            "updated_at": self._updated_at,
            "message_url": msg_url,
            "chat_id": chat_id,
            "message_id": msg_id,
            "file_id": pointer.get("file_id") if pointer else None,
        }

    async def _upload_manifest_document(
        self, bot: Client, manifest_dict: Dict[str, Any], version: int
    ) -> Any:
        temp_dir = tempfile.gettempdir()
        temp_path = Path(temp_dir) / f"db_manifest_v{version}_{uuid.uuid4().hex[:8]}.json"

        try:
            with open(temp_path, "wb") as f:
                f.write(_dumps_json(manifest_dict))

            msg = await bot.send_document(
                chat_id=self.settings.LOGGER_GROUP_ID,
                document=str(temp_path),
                file_name="db.json",
                caption=f"🗄 <b>Manifest db.json</b> (v{version})\nIndexed files: {len(manifest_dict.get('files', []))}\nUpdated: {manifest_dict.get('updated_at')}",
                parse_mode=enums.ParseMode.HTML,
            )
            return msg
        finally:
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
