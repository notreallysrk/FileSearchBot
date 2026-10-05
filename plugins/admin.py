# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Any

from pyrogram import Client, enums
from pyrogram.types import Message

from config import Settings
from database.settings import SystemSettingsRepository
from lang.manager import tr
from utils.formatting import escape_html
from utils.logging import get_logger

logger = get_logger("plugins.admin")

SENSITIVE_KEYS = {
    "MASTER_BOT_TOKEN",
    "DELIVERY_BOT_TOKEN",
    "TOKEN_SECRET_KEY",
    "MONGO_URI",
    "WEBHOOK_SECRET",
    "API_HASH",
}

def mask_value(key: str, value: str) -> str:
    if key.upper() in SENSITIVE_KEYS and len(value) > 8:
        return f"{value[:4]}...{value[-4:]}"
    return value

async def handle_vars_command(
    client: Client,
    message: Message,
    settings: Settings,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    env_path = Path(".env")
    env_vars: dict[str, str] = {}

    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip("\"'")
        except Exception as exc:
            logger.warning("Could not read .env: %s", exc)

    if not env_vars:
        for k in settings.model_fields.keys():
            val = getattr(settings, k, None)
            if val is not None:
                env_vars[k] = str(val)

    lines = [tr("admin_vars_header", "en")]
    for k in sorted(env_vars.keys()):
        masked = mask_value(k, env_vars[k])
        lines.append(f"• <code>{k}</code> = <code>{masked}</code>")

    lines.append(tr("admin_vars_footer", "en"))
    await message.reply_text("\n".join(lines), parse_mode=enums.ParseMode.HTML)

async def handle_setvar_command(
    client: Client,
    message: Message,
    settings: Settings,
    ecosystem: Optional[Any] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    text_parts = (message.text or "").strip().split(maxsplit=2)
    if len(text_parts) < 3:
        await message.reply_text(
            tr("admin_setvar_usage", "en"),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    var_name = text_parts[1].strip().upper()
    var_value = text_parts[2].strip()

    env_path = Path(".env")
    lines: list[str] = []
    found = False

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, _ = stripped.split("=", 1)
                    if k.strip().upper() == var_name:
                        lines.append(f"{var_name}={var_value}\n")
                        found = True
                        continue
                lines.append(line)

    if not found:
        lines.append(f"{var_name}={var_value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    os.environ[var_name] = var_value

    masked = mask_value(var_name, var_value)
    await message.reply_text(
        tr("admin_setvar_success", "en", var_name=var_name, masked=masked),
        parse_mode=enums.ParseMode.HTML,
    )

    logger.info("Restarting bot process after /setvar %s...", var_name)
    asyncio.create_task(restart_bot_process(ecosystem))

async def restart_bot_process(ecosystem: Optional[Any] = None) -> None:
    await asyncio.sleep(1.0)
    if ecosystem:
        try:
            await ecosystem.shutdown()
        except Exception as exc:
            logger.warning("Error during ecosystem shutdown before restart: %s", exc)

    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen([sys.executable] + sys.argv, creationflags=flags)
        sys.exit(0)
    else:
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)

async def handle_restart_command(
    client: Client,
    message: Message,
    settings: Settings,
    ecosystem: Optional[Any] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    await message.reply_text(
        tr("admin_restart_notice", "en", platform=sys.platform),
        parse_mode=enums.ParseMode.HTML,
    )

    logger.info("Executing /restart command from owner %d on %s", user.id, sys.platform)
    asyncio.create_task(restart_bot_process(ecosystem))

async def handle_maintain_command(
    client: Client,
    message: Message,
    settings: Settings,
    system_settings_repo: Optional[SystemSettingsRepository] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    if not system_settings_repo:
        await message.reply_text("⚠️ System settings repository is unavailable.", parse_mode=enums.ParseMode.HTML)
        return

    text_parts = (message.text or "").strip().split(maxsplit=1)
    arg = text_parts[1].strip().lower() if len(text_parts) > 1 else ""

    if arg in ("on", "enable", "1", "true"):
        await system_settings_repo.set_maintenance_mode(True)
        await message.reply_text(
            tr("admin_maintain_enabled", "en"),
            parse_mode=enums.ParseMode.HTML,
        )
    elif arg in ("off", "disable", "0", "false"):
        await system_settings_repo.set_maintenance_mode(False)
        await message.reply_text(
            tr("admin_maintain_disabled", "en"),
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        current_status = "ENABLED 🔴" if system_settings_repo.is_maintenance_mode else "DISABLED 🟢"
        await message.reply_text(
            tr("admin_maintain_status", "en", status=current_status),
            parse_mode=enums.ParseMode.HTML,
        )

async def handle_allow_command(
    client: Client,
    message: Message,
    settings: Settings,
    system_settings_repo: Optional[SystemSettingsRepository] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return
    if not system_settings_repo:
        return

    text_parts = (message.text or "").strip().split(maxsplit=1)
    target_chat = None
    if len(text_parts) > 1:
        raw = text_parts[1].strip()
        if raw.lstrip("-").isdigit():
            target_chat = int(raw)
    elif message.chat.type != enums.ChatType.PRIVATE:
        target_chat = message.chat.id

    if not target_chat:
        await message.reply_text(tr("admin_allow_usage", "en"), parse_mode=enums.ParseMode.HTML)
        return

    success = await system_settings_repo.allow_chat(target_chat)
    if success:
        await message.reply_text(tr("admin_allow_success", "en", chat_id=target_chat), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text(tr("admin_allow_exists", "en", chat_id=target_chat), parse_mode=enums.ParseMode.HTML)

async def handle_disallow_command(
    client: Client,
    message: Message,
    settings: Settings,
    system_settings_repo: Optional[SystemSettingsRepository] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return
    if not system_settings_repo:
        return

    text_parts = (message.text or "").strip().split(maxsplit=1)
    target_chat = None
    if len(text_parts) > 1:
        raw = text_parts[1].strip()
        if raw.lstrip("-").isdigit():
            target_chat = int(raw)
    elif message.chat.type != enums.ChatType.PRIVATE:
        target_chat = message.chat.id

    if not target_chat:
        await message.reply_text(tr("admin_disallow_usage", "en"), parse_mode=enums.ParseMode.HTML)
        return

    success = await system_settings_repo.disallow_chat(target_chat)
    if success:
        await message.reply_text(tr("admin_disallow_success", "en", chat_id=target_chat), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text(tr("admin_disallow_not_found", "en", chat_id=target_chat), parse_mode=enums.ParseMode.HTML)

async def handle_allowed_command(
    client: Client,
    message: Message,
    settings: Settings,
    system_settings_repo: Optional[SystemSettingsRepository] = None,
) -> None:
    user = message.from_user
    if not user or not settings.is_owner(user.id):
        return

    chats = list(system_settings_repo.allowed_chats) if system_settings_repo else []
    default_files = settings.FILES_GROUP_ID
    all_chats = []
    if default_files:
        all_chats.append(default_files)
    for c in sorted(chats):
        if c != default_files:
            all_chats.append(c)

    lines = [tr("admin_allowed_header", "en")]
    for c in all_chats:
        is_default = (c == default_files)
        suffix = " <i>(Default Files Group)</i>" if is_default else ""
        try:
            chat_obj = await client.get_chat(c)
            title = chat_obj.title or chat_obj.first_name or str(c)
            status_prefix = "✅"
            line = f"• {status_prefix} <b>{escape_html(title)}</b> (<code>{c}</code>){suffix}"
        except Exception:
            status_prefix = "⚠️"
            line = f"• {status_prefix} <code>{c}</code> <i>(Inaccessible / Error)</i>{suffix}"
        lines.append(line)

    lines.append(tr("admin_allowed_footer", "en"))
    await message.reply_text("\n".join(lines), parse_mode=enums.ParseMode.HTML)
