# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import time
from typing import Optional, Any
from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import Settings
from client.mongodb import MongoDB
from client.master_bot import register_master_handlers
from client.delivery_bot import register_delivery_handlers
from database import (
    ensure_indexes,
    UserRepository,
    BlockedUserRepository,
    RequestRepository,
    StatisticsRepository,
    ManifestRepository,
    TokenRegistryRepository,
    SystemSettingsRepository,
)
from keyboards.pagination import PaginationManager
from middlewares.pipeline import SecurityPipeline
from services import (
    SearchEngine,
    FileTokenService,
    ManifestManager,
    SubscriptionService,
    StatisticsManager,
    RequestManager,
    FileDeliveryService,
    EventLoggerService,
)
from services.scanner import ScannerService
from utils.logging import get_logger

logger = get_logger("client.bots")

class BotEcosystem:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.start_time: float = time.time()

        self.mongodb = MongoDB(settings)

        self.user_repo: Optional[UserRepository] = None
        self.blocked_repo: Optional[BlockedUserRepository] = None
        self.request_repo: Optional[RequestRepository] = None
        self.stats_repo: Optional[StatisticsRepository] = None
        self.manifest_repo: Optional[ManifestRepository] = None
        self.token_repo: Optional[TokenRegistryRepository] = None
        self.system_settings_repo: Optional[SystemSettingsRepository] = None

        self.search_engine: Optional[SearchEngine] = None
        self.manifest_manager: Optional[ManifestManager] = None
        self.token_service: Optional[FileTokenService] = None
        self.file_delivery_service: Optional[FileDeliveryService] = None
        self.subscription_service: Optional[SubscriptionService] = None
        self.stats_manager: Optional[StatisticsManager] = None
        self.pagination_manager: Optional[PaginationManager] = None
        self.scanner_service: Optional[ScannerService] = None
        self.security_pipeline: Optional[SecurityPipeline] = None

        self.master_bot: Optional[Client] = None
        self.delivery_bot: Optional[Client] = None
        self.event_logger: Optional[EventLoggerService] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running_event: Optional[asyncio.Event] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        logger.info("Initializing Bot Ecosystem (Kurigram MTProto)...")

        await self.mongodb.connect()
        db = self.mongodb.db

        self.user_repo = UserRepository(db)
        self.blocked_repo = BlockedUserRepository(db)
        await self.blocked_repo.load_cache()
        self.request_repo = RequestRepository(db)
        self.stats_repo = StatisticsRepository(db)
        self.manifest_repo = ManifestRepository(db)
        self.token_repo = TokenRegistryRepository(db)
        self.system_settings_repo = SystemSettingsRepository(db)
        await self.system_settings_repo.load()

        await ensure_indexes(db)

        self.search_engine = SearchEngine(
            cache_size=self.settings.SEARCH_CACHE_SIZE,
            strict_and=self.settings.SEARCH_STRICT_AND,
            fuzzy_enabled=self.settings.SEARCH_FUZZY_ENABLED,
            fuzzy_threshold=self.settings.SEARCH_FUZZY_THRESHOLD,
        )
        self.manifest_manager = ManifestManager(
            settings=self.settings,
            manifest_repo=self.manifest_repo,
            search_engine=self.search_engine,
        )
        self.token_service = FileTokenService(
            token_repo=self.token_repo,
            default_ttl=self.settings.TOKEN_EXPIRY_SECONDS,
        )
        self.subscription_service = SubscriptionService(self.settings)
        await self.subscription_service.load_from_db(db)

        self.stats_manager = StatisticsManager(self.stats_repo)
        await self.stats_manager.start()

        self.file_delivery_service = FileDeliveryService(
            token_service=self.token_service,
            search_engine=self.search_engine,
            user_repo=self.user_repo,
            blocked_repo=self.blocked_repo,
            stats_manager=self.stats_manager,
            auto_delete_seconds=self.settings.AUTO_DELETE_FILE_SECONDS,
        )
        self.pagination_manager = PaginationManager(
            settings=self.settings,
            token_service=self.token_service,
        )
        self.request_manager = RequestManager(
            settings=self.settings,
            request_repo=self.request_repo,
        )
        self.scanner_service = ScannerService(
            settings=self.settings,
            manifest_manager=self.manifest_manager,
        )

        self.master_bot = Client(
            name="master_bot",
            api_id=self.settings.API_ID,
            api_hash=self.settings.API_HASH,
            bot_token=self.settings.MASTER_BOT_TOKEN,
            in_memory=True,
        )
        self.event_logger = EventLoggerService(self.settings, self.master_bot)
        self.subscription_service.event_logger = self.event_logger

        self.security_pipeline = SecurityPipeline(
            settings=self.settings,
            user_repo=self.user_repo,
            blocked_repo=self.blocked_repo,
            subscription_service=self.subscription_service,
            system_settings_repo=self.system_settings_repo,
            event_logger=self.event_logger,
        )

        if self.settings.is_dual_bot:
            self.delivery_bot = Client(
                name="delivery_bot",
                api_id=self.settings.API_ID,
                api_hash=self.settings.API_HASH,
                bot_token=self.settings.DELIVERY_BOT_TOKEN,
                in_memory=True,
            )
            register_delivery_handlers(self.delivery_bot, self)
        else:
            self.delivery_bot = None

        register_master_handlers(self.master_bot, self)

        self._initialized = True
        logger.info("Bot Ecosystem initialization complete")

    async def register_commands(self) -> None:
        user_commands = [
            BotCommand(command="start", description="Start or restart the bot"),
            BotCommand(command="explore", description="Browse file library"),
            BotCommand(command="random", description="Get random files"),
            BotCommand(command="request", description="Request an unlisted file"),
            BotCommand(command="lang", description="Change language"),
            BotCommand(command="cancel", description="Cancel active operation"),
            BotCommand(command="help", description="Show help and command list"),
        ]

        owner_commands = [
            BotCommand(command="start", description="Restart bot or open welcome screen"),
            BotCommand(command="explore", description="Explore file collection"),
            BotCommand(command="random", description="Get random files"),
            BotCommand(command="help", description="Show search and full admin guide"),
            BotCommand(command="stats", description="System metrics"),
            BotCommand(command="scan", description="Scan messages in group/channel for files"),
            BotCommand(command="allow", description="Allow group for indexing"),
            BotCommand(command="disallow", description="Disallow group from indexing"),
            BotCommand(command="allowed", description="List allowed indexing groups"),
            BotCommand(command="vars", description="View environment variables"),
            BotCommand(command="setvar", description="Update .env variable and restart"),
            BotCommand(command="maintain", description="Toggle maintenance mode on/off"),
            BotCommand(command="restart", description="Restart bot process"),
            BotCommand(command="blocked", description="List blocked users"),
            BotCommand(command="request", description="Request an unlisted file"),
            BotCommand(command="lang", description="Change language"),
            BotCommand(command="cancel", description="Cancel active operation"),
        ]

        delivery_commands = [
            BotCommand(command="start", description="Retrieve file via delivery link"),
            BotCommand(command="random", description="Get random files"),
        ]

        try:
            await self.master_bot.set_bot_commands(user_commands, scope=BotCommandScopeDefault())
            for owner_id in self.settings.OWNER_IDS:
                try:
                    await self.master_bot.set_bot_commands(
                        owner_commands,
                        scope=BotCommandScopeChat(chat_id=owner_id),
                    )
                except Exception as exc:
                    logger.debug("Could not register scoped owner commands for %d: %s", owner_id, exc)

            if self.settings.is_dual_bot and self.delivery_bot:
                await self.delivery_bot.set_bot_commands(delivery_commands, scope=BotCommandScopeDefault())

            logger.info("Telegram bot menu commands registered (User + Owner scopes)")
        except Exception as exc:
            logger.warning("Could not register bot menu commands: %s", exc)

    async def start_polling(self) -> None:
        if not self._initialized:
            await self.initialize()

        logger.info("Starting Master Bot client...")
        await self.master_bot.start()

        try:
            master_me = await self.master_bot.get_me()
            self.settings.MASTER_BOT_USERNAME = master_me.username or self.settings.MASTER_BOT_USERNAME
            logger.info("Discovered Master Bot username: @%s", self.settings.MASTER_BOT_USERNAME)
        except Exception as exc:
            logger.warning("Could not auto-fetch Master Bot username: %s", exc)

        if self.settings.is_dual_bot and self.delivery_bot and self.delivery_bot is not self.master_bot:
            logger.info("Starting Delivery Bot client...")
            await self.delivery_bot.start()
            try:
                delivery_me = await self.delivery_bot.get_me()
                self.settings.DELIVERY_BOT_USERNAME = delivery_me.username or self.settings.DELIVERY_BOT_USERNAME
                logger.info("Discovered Delivery Bot username: @%s", self.settings.DELIVERY_BOT_USERNAME)
            except Exception as exc:
                logger.warning("Could not auto-fetch Delivery Bot username: %s", exc)

        await self.register_commands()

        try:
            await self.manifest_manager.initialize_and_load(self.master_bot)
        except Exception as exc:
            logger.warning("Initial manifest recovery non-fatal warning: %s", exc)

        if self.event_logger:
            asyncio.create_task(
                self.event_logger.notify_bot_started(
                    bot_username=self.settings.MASTER_BOT_USERNAME,
                    version=self.manifest_manager.version,
                    total_files=self.manifest_manager.files_count,
                )
            )

        self._monitor_task = asyncio.create_task(self._monitor_ram_load(), name="ram_monitor_task")
        self._running_event = asyncio.Event()
        await self._running_event.wait()

    async def _monitor_ram_load(self) -> None:
        import psutil
        proc = psutil.Process()
        while True:
            try:
                await asyncio.sleep(30.0)
                rss_mb = proc.memory_info().rss / (1024.0 * 1024.0)
                if rss_mb > 400.0 and self.event_logger:
                    await self.event_logger.notify_high_ram(ram_mb=rss_mb, threshold_mb=400.0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("RAM monitor check error: %s", exc)

    async def shutdown(self) -> None:
        logger.info("Shutting down Bot Ecosystem...")

        if self._running_event:
            self._running_event.set()

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

        if self.manifest_manager and self.manifest_manager.is_dirty:
            logger.info("Flushing uncommitted manifest changes before shutdown...")
            try:
                await self.manifest_manager.flush_manifest(self.master_bot)
            except Exception as exc:
                logger.warning("Could not flush manifest on shutdown: %s", exc)

        if self.stats_manager:
            await self.stats_manager.stop()

        if self.master_bot and getattr(self.master_bot, "is_connected", False):
            try:
                await self.master_bot.stop()
            except Exception as exc:
                logger.debug("Master bot stop error: %s", exc)

        if self.settings.is_dual_bot and self.delivery_bot and self.delivery_bot is not self.master_bot and getattr(self.delivery_bot, "is_connected", False):
            try:
                await self.delivery_bot.stop()
            except Exception as exc:
                logger.debug("Delivery bot stop error: %s", exc)

        await self.mongodb.close()
        self._initialized = False
        logger.info("Bot Ecosystem successfully shut down")
