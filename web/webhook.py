# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import hmac
from aiohttp import web
from client.bots import BotEcosystem
from utils.logging import get_logger

logger = get_logger("web.webhook")

def _verify_secret_token(request: web.Request, expected_secret: str) -> bool:
    header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not expected_secret or not header:
        return False
    return hmac.compare_digest(header, expected_secret)

async def master_webhook_handler(request: web.Request) -> web.Response:
    return web.Response(status=200, text="MTProto Active")

async def delivery_webhook_handler(request: web.Request) -> web.Response:
    return web.Response(status=200, text="MTProto Active")
