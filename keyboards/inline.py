# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations
from typing import List, Tuple, Union, Optional
from pyrogram import enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from lang.manager import tr

_orig_btn_init = InlineKeyboardButton.__init__

def _patched_btn_init(self, *args, style=enums.ButtonStyle.DEFAULT, **kwargs):
    if isinstance(style, str):
        style = getattr(enums.ButtonStyle, style.upper(), enums.ButtonStyle.DEFAULT)
    return _orig_btn_init(self, *args, style=style, **kwargs)

InlineKeyboardButton.__init__ = _patched_btn_init

def get_start_keyboard(support_url: str, backup_url: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="🧭 Explore", callback_data="explore", style="primary"),
                InlineKeyboardButton(text=tr("btn_help", lang), callback_data="help_menu", style="primary"),
            ],
            [
                InlineKeyboardButton(text=tr("btn_support_group", lang), url=support_url, style="primary"),
                InlineKeyboardButton(text=tr("btn_backup_channel", lang), url=backup_url, style="primary"),
            ],
        ]
    )

def get_help_keyboard(support_url: str = "", from_start: bool = False, lang: str = "en") -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []
    if from_start:
        row: List[InlineKeyboardButton] = []
        if support_url:
            row.append(InlineKeyboardButton(text=tr("btn_support_group", lang), url=support_url, style="primary"))
        row.append(InlineKeyboardButton(text=tr("btn_back", lang), callback_data="start_menu", style="primary"))
        buttons.append(row)
    else:
        if support_url:
            buttons.append([InlineKeyboardButton(text=tr("btn_support_group", lang), url=support_url, style="primary")])
    return InlineKeyboardMarkup(buttons)

def get_open_pm_keyboard(bot_username: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=tr("btn_open_pm", lang),
                    url=f"https://t.me/{bot_username}?start=group",
                    style="success",
                )
            ]
        ]
    )

def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en", style="primary"),
                InlineKeyboardButton(text="🇮🇳 हिन्दी", callback_data="set_lang:hi", style="primary"),
            ]
        ]
    )

def get_empty_search_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text=tr("btn_request_file", lang), callback_data="make_request", style="primary")]
        ]
    )

def get_redirect_to_master_keyboard(master_username: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=tr("btn_back_to_search", lang),
                    url=f"https://t.me/{master_username}",
                    style="primary",
                )
            ]
        ]
    )

def get_blocked_users_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons: List[InlineKeyboardButton] = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"blk_pg:{page - 1}", style="primary"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop", style="default"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"blk_pg:{page + 1}", style="primary"))

    return InlineKeyboardMarkup([buttons] if buttons else [])

def get_maintenance_keyboard(support_url: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text=tr("btn_support_channel", lang), url=support_url, style="primary"),
            ]
        ]
    )

def get_subscription_keyboard(missing: List[Tuple[Union[str, int], str]], lang: str = "en") -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []
    for idx, (channel, url) in enumerate(missing, start=1):
        name = channel if isinstance(channel, str) and channel.startswith("@") else f"Channel {idx}"
        btn_text = f"{tr('btn_join_channel', lang)} ({name})"
        buttons.append([InlineKeyboardButton(text=btn_text, url=url, style="primary")])

    buttons.append([InlineKeyboardButton(text=tr("btn_confirm_sub", lang), callback_data="confirm_sub", style="success")])
    return InlineKeyboardMarkup(buttons)

def get_scanner_keyboard(session_id: str, paused: bool = False, resting: bool = False) -> InlineKeyboardMarkup:
    if paused:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="▶ Resume", callback_data=f"scan:resume:{session_id}", style="success"),
                    InlineKeyboardButton(text="⏹ Stop", callback_data=f"scan:stop:{session_id}", style="danger"),
                ]
            ]
        )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="⏸ Pause", callback_data=f"scan:pause:{session_id}", style="primary"),
                InlineKeyboardButton(text="⏹ Stop", callback_data=f"scan:stop:{session_id}", style="danger"),
            ]
        ]
    )

def get_request_admin_keyboard(request_id: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=tr("request_btn_mark_uploaded", lang),
                    callback_data=f"req_up:{request_id}",
                    style="success",
                )
            ]
        ]
    )

def get_random_dual_keyboard(delivery_username: str, count: int, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=tr("btn_random_dual", lang, count=count),
                    url=f"https://t.me/{delivery_username}?start=random_{count}",
                    style="success",
                )
            ]
        ]
    )

def get_group_search_keyboard(bot_username: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🚀 Search in Bot PM",
                    url=f"https://t.me/{bot_username}?start=group",
                    style="primary",
                )
            ]
        ]
    )
