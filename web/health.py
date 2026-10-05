# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

from aiohttp import web
from client.bots import BotEcosystem

async def health_check_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy"})

async def readiness_check_handler(request: web.Request) -> web.Response:
    ecosystem: BotEcosystem = request.app["ecosystem"]
    is_ready = False
    db_connected = False

    try:
        db_connected = await ecosystem.mongodb.ping()
        is_ready = db_connected and ecosystem._initialized
    except Exception:
        db_connected = False
        is_ready = False

    status_code = 200 if is_ready else 503
    return web.json_response(
        {
            "status": "ready" if is_ready else "degraded",
            "database_connected": db_connected,
            "manifest_version": ecosystem.manifest_manager.version if ecosystem.manifest_manager else 0,
            "files_indexed": ecosystem.manifest_manager.files_count if ecosystem.manifest_manager else 0,
        },
        status=status_code,
    )
