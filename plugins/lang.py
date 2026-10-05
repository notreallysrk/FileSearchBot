# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import Optional
from pyrogram import Client, enums
from pyrogram.types import Message, CallbackQuery

from database.users import UserRepository
from keyboards.inline import get_language_keyboard
from lang.manager import tr

async def handle_language_command(client: Client, message: Message, lang: str = "en") -> None:
    await message.reply_text(
        tr("lang_choose", lang),
        reply_markup=get_language_keyboard(),
        parse_mode=enums.ParseMode.HTML,
    )

async def handle_language_callback(client: Client, callback: CallbackQuery, user_repo: UserRepository) -> None:
    user = callback.from_user
    if not user:
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 2:
        return

    target_lang = parts[1]
    if target_lang not in ("en", "hi"):
        target_lang = "en"

    await user_repo.set_language(user.id, target_lang)
    confirm_text = tr("lang_updated", target_lang)

    try:
        if callback.message:
            await callback.message.edit_text(confirm_text, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass

    await callback.answer(confirm_text)
