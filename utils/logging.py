# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import logging
import re
import sys
from typing import Optional

TOKEN_REGEX = re.compile(r"(\d{8,12}:[a-zA-Z0-9_-]{35,})")
MONGO_PW_REGEX = re.compile(r"(mongodb(?:\+srv)?://[^:]+:)([^@]+)(@)")

class SafeFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)

        scrubbed = TOKEN_REGEX.sub(r"[REDACTED_BOT_TOKEN]", original)

        scrubbed = MONGO_PW_REGEX.sub(r"\1***\3", scrubbed)
        return scrubbed

def setup_logging(level: str = "INFO") -> logging.Logger:
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = SafeFormatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger("telegram_file_bot")
    logger.setLevel(log_level)
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name:
        return logging.getLogger(f"telegram_file_bot.{name}")
    return logging.getLogger("telegram_file_bot")
