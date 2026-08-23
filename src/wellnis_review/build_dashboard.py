"""Write docs/data.json — the JSON the static dashboard (docs/index.html) fetches.

Kept as a plain file committed alongside the code so GitHub Pages (serving the
`docs/` folder) needs no backend.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import DASHBOARD_DATA_FILE


def build_dashboard_data(branches_out: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branches": branches_out,
    }


def write_dashboard_data(data: dict[str, Any]) -> None:
    DASHBOARD_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
