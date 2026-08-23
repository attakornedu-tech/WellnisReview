"""Minimal Telegram Bot API client (sendMessage only, via HTTP)."""
from __future__ import annotations

import time

import requests

TELEGRAM_API = "https://api.telegram.org"
MAX_LEN = 4000  # Telegram hard limit is 4096; leave headroom for HTML tag splits


def _chunk(text: str, max_len: int = MAX_LEN) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    remaining = text
    while len(remaining) > max_len:
        split_at = remaining.rfind("\n\n", 0, max_len)
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def send_message(bot_token: str, chat_id: str, text: str, retries: int = 3) -> None:
    """Send one logical message, split into multiple Telegram messages if too long."""
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    for chunk in _chunk(text):
        last_err = None
        for attempt in range(retries):
            resp = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            if resp.status_code == 200 and resp.json().get("ok"):
                last_err = None
                break
            last_err = f"{resp.status_code}: {resp.text[:300]}"
            time.sleep(2 * (attempt + 1))
        if last_err:
            raise RuntimeError(f"Telegram sendMessage failed: {last_err}")
