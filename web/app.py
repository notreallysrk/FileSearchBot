# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from aiohttp import web
from client.bots import BotEcosystem
from web.health import health_check_handler, readiness_check_handler
from web.webhook import master_webhook_handler, delivery_webhook_handler
from utils.logging import get_logger

logger = get_logger("web.app")

def create_web_app(ecosystem: BotEcosystem) -> web.Application:
    app = web.Application()
    app["ecosystem"] = ecosystem

    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/ready", readiness_check_handler)

    app.router.add_post("/webhook/master", master_webhook_handler)
    app.router.add_post("/webhook/delivery", delivery_webhook_handler)

    return app

async def start_web_server(ecosystem: BotEcosystem) -> web.AppRunner:
    app = create_web_app(ecosystem)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=ecosystem.settings.WEB_SERVER_HOST, port=ecosystem.settings.WEB_SERVER_PORT)
    await site.start()
    logger.info(
        "HTTP server running on http://%s:%d (health: /health, ready: /ready)",
        ecosystem.settings.WEB_SERVER_HOST,
        ecosystem.settings.WEB_SERVER_PORT,
    )
    return runner
