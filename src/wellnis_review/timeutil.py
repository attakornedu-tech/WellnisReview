"""Time helpers shared by state_store and run_daily.

Google Places API returns publishTime as RFC3339 UTC with up to nanosecond
fractional precision (e.g. "2026-05-09T15:59:04.360708120Z"), which Python's
datetime.fromisoformat cannot parse directly (it accepts at most 6 fractional
digits) — parse_iso below truncates to microseconds before parsing.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")

_ISO_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?Z$")


def parse_iso(iso: str) -> datetime:
    m = _ISO_RE.match(iso)
    if not m:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    base, frac = m.groups()
    micros = "." + frac[1:][:6].ljust(6, "0") if frac else ""
    return datetime.fromisoformat(base + micros + "+00:00")


def bkk_date(iso: str) -> date:
    return parse_iso(iso).astimezone(BANGKOK).date()


def today_bkk(now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(BANGKOK).date()


def is_today_bkk(iso: str, now: datetime | None = None) -> bool:
    """True if the given RFC3339 timestamp falls on today's calendar date in
    Asia/Bangkok — this is the definition of "รีวิวใหม่วันนี้", not whether our
    system happens to be seeing the review for the first time."""
    return bkk_date(iso) == today_bkk(now)


def fmt_dt_bkk(iso: str) -> str:
    dt = parse_iso(iso).astimezone(BANGKOK)
    return dt.strftime("%d/%m/%Y %H:%M") + " น."
