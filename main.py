# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import signal
import sys
from typing import Optional
from aiohttp import web

from config import settings
from client.bots import BotEcosystem
from web.app import start_web_server
from utils.logging import setup_logging, get_logger

logger = get_logger("main")

async def main() -> None:
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("Starting Telegram File Sharing & Search Bot (Kurigram MTProto)...")
    logger.info("Configuration: %r", settings)

    ecosystem = BotEcosystem(settings)
    web_runner: Optional[web.AppRunner] = None
    stop_event = asyncio.Event()

    def _handle_exit_signal(sig_name: str) -> None:
        logger.info("Received shutdown signal: %s", sig_name)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig.name: _handle_exit_signal(s))
        except (NotImplementedError, RuntimeError):
            pass

    try:
        await ecosystem.initialize()

        try:
            web_runner = await start_web_server(ecosystem)
        except Exception as exc:
            logger.warning("Could not start HTTP server on port %d: %s", settings.WEB_SERVER_PORT, exc)

        polling_task = asyncio.create_task(ecosystem.start_polling(), name="bots_polling")
        wait_stop = asyncio.create_task(stop_event.wait(), name="stop_event_wait")

        done, pending = await asyncio.wait(
            [polling_task, wait_stop],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for p in pending:
            p.cancel()
        for d in done:
            if d == polling_task and not d.cancelled():
                err = d.exception()
                if err:
                    logger.error("Polling halted due to error: %s", err)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Execution interrupted by user or system signal.")
    except Exception as exc:
        logger.exception("Fatal runtime error during startup: %s", exc)
        sys.exit(1)
    finally:
        logger.info("Initiating graceful shutdown sequence...")
        if ecosystem._initialized:
            try:
                await ecosystem.shutdown()
            except Exception as exc:
                logger.warning("Error during ecosystem shutdown: %s", exc)

        if web_runner:
            try:
                await web_runner.cleanup()
            except Exception as exc:
                logger.warning("Error during web server cleanup: %s", exc)

        logger.info("Bot ecosystem shutdown complete. Process exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
