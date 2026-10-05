# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Any
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery

from plugins.file_delivery import (
    handle_delivery_start_command,
    handle_delivery_plain_text,
    handle_random_command,
)
from plugins.errors import handle_client_error

def register_delivery_handlers(client: Client, ecosystem: Any) -> None:
    pipeline = ecosystem.security_pipeline

    async def on_message_handler(c: Client, m: Message) -> None:
        user = m.from_user
        if not user or user.is_bot:
            return

        user_lang = await ecosystem.user_repo.get_language(user.id)
        allowed = await pipeline.check_message(c, m, require_sub=False)
        if not allowed:
            return

        text = (m.text or "").strip()
        try:
            if text.startswith("/start"):
                await handle_delivery_start_command(
                    client=c,
                    message=m,
                    settings=ecosystem.settings,
                    file_delivery_service=ecosystem.file_delivery_service,
                    subscription_service=ecosystem.subscription_service,
                    user_repo=ecosystem.user_repo,
                    master_bot=ecosystem.master_bot,
                    lang=user_lang,
                )
            elif text.startswith("/random"):
                await handle_random_command(
                    client=c,
                    message=m,
                    settings=ecosystem.settings,
                    file_delivery_service=ecosystem.file_delivery_service,
                    subscription_service=ecosystem.subscription_service,
                    user_repo=ecosystem.user_repo,
                    master_bot=ecosystem.master_bot,
                    lang=user_lang,
                )
            elif m.chat.type == ChatType.PRIVATE:
                await handle_delivery_plain_text(
                    client=c,
                    message=m,
                    settings=ecosystem.settings,
                    lang=user_lang,
                )
        except Exception as exc:
            await handle_client_error(c, m, exc, ecosystem.event_logger)

    async def on_callback_query_handler(c: Client, cb: CallbackQuery) -> None:
        allowed = await pipeline.check_callback(c, cb)
        if not allowed:
            return
        await cb.answer()

    client.add_handler(MessageHandler(on_message_handler))
    client.add_handler(CallbackQueryHandler(on_callback_query_handler))
