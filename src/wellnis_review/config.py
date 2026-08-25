"""Config loading: branches.json + environment variables."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANCHES_FILE = ROOT / "branches.json"
STATE_FILE = ROOT / "data" / "state.json"
DASHBOARD_DATA_FILE = ROOT / "docs" / "data.json"

# ต่ำกว่าหรือเท่ากับกี่ดาว ถึงจะถือว่าต้องแจ้งเตือนด่วน (ตามความต้องการ: 3 ดาวหรือน้อยกว่า)
LOW_RATING_THRESHOLD = 3


@dataclass(frozen=True)
class Branch:
    key: str
    name: str
    maps_url: str
    place_id: str | None


def load_branches() -> list[Branch]:
    raw = json.loads(BRANCHES_FILE.read_text(encoding="utf-8"))
    return [
        Branch(
            key=b["key"],
            name=b["name"],
            maps_url=b["maps_url"],
            place_id=b.get("place_id"),
        )
        for b in raw["branches"]
    ]


def save_branches(branches: list[Branch]) -> None:
    raw = json.loads(BRANCHES_FILE.read_text(encoding="utf-8"))
    by_key = {b["key"]: b for b in raw["branches"]}
    for b in branches:
        if b.key in by_key:
            by_key[b.key]["place_id"] = b.place_id
    BRANCHES_FILE.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def env(name: str, required: bool = True, default: str | None = None) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val
