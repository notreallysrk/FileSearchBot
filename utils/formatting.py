# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import html
from typing import Optional

def format_file_size(size_bytes: Optional[int]) -> str:
    if size_bytes is None or size_bytes < 0:
        return "N/A"
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"

def escape_html(text: Optional[str]) -> str:
    if not text:
        return ""
    return html.escape(str(text), quote=False)

def format_result_button_text(caption: str, file_size: Optional[int], max_length: int = 35) -> str:
    size_str = format_file_size(file_size)
    size_suffix = f" ({size_str})" if size_str != "N/A" else ""

    available_len = max_length - len(size_suffix)
    if available_len <= 5:
        available_len = 10

    clean_caption = " ".join((caption or "File").split())
    if len(clean_caption) > available_len:
        cutoff = available_len - 3
        clean_caption = clean_caption[:cutoff].rstrip() + "..."

    return f"{clean_caption}{size_suffix}"

def format_duration(seconds: float) -> str:
    if seconds < 0:
        return "0s"
    total_sec = int(seconds)
    days, rem = divmod(total_sec, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
