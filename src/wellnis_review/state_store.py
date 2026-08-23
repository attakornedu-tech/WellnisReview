"""Persisted per-branch state: which reviews we've already seen, running totals,
and a capped local review corpus used for the AI "คำชมบ่อยๆ" summary.

Stored at data/state.json and committed back to the repo by the daily GitHub
Action, so history survives across runs (Actions runners are ephemeral).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import MAX_REVIEWS_KEPT_PER_BRANCH, STATE_FILE


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"branches": {}}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_review(raw: dict) -> dict:
    text = ""
    if raw.get("text", {}).get("text"):
        text = raw["text"]["text"]
    elif raw.get("originalText", {}).get("text"):
        text = raw["originalText"]["text"]
    return {
        "name": raw.get("name", ""),
        "author": raw.get("authorAttribution", {}).get("displayName", "ไม่ทราบชื่อ"),
        "rating": raw.get("rating"),
        "text": text,
        "publish_time": raw.get("publishTime"),
        "relative_time": raw.get("relativePublishTimeDescription", ""),
    }


def update_branch_state(
    state: dict[str, Any],
    branch_key: str,
    details: dict,
) -> dict[str, Any]:
    """Merge fresh Place Details into state; return a per-branch sync report:

    {
        "rating": float | None,
        "user_ratings_total": int | None,
        "new_reviews": [review, ...],       # not previously seen, this run
        "low_rating_alerts": [review, ...], # subset of new_reviews with rating <= threshold
        "last_review_time": str | None,     # newest publish_time ever seen (even if 0 new today)
        "reviews_corpus": [review, ...],    # capped local history, for AI summary
    }
    """
    from .config import LOW_RATING_THRESHOLD

    branches = state.setdefault("branches", {})
    b_state = branches.setdefault(branch_key, {"reviews": {}})

    incoming = [parse_review(r) for r in details.get("reviews", [])]
    existing_reviews: dict[str, dict] = b_state.get("reviews", {})

    new_reviews: list[dict] = []
    for r in incoming:
        key = r["name"] or f"{r['author']}|{r['publish_time']}"
        if key and key not in existing_reviews:
            r_with_meta = dict(r, first_seen=_now_iso())
            existing_reviews[key] = r_with_meta
            new_reviews.append(r_with_meta)

    # เก็บย้อนหลังไว้ไม่เกิน MAX_REVIEWS_KEPT_PER_BRANCH รายการ (ตัดของเก่าสุดทิ้งตาม publish_time)
    if len(existing_reviews) > MAX_REVIEWS_KEPT_PER_BRANCH:
        ordered = sorted(
            existing_reviews.items(),
            key=lambda kv: kv[1].get("publish_time") or "",
            reverse=True,
        )
        existing_reviews = dict(ordered[:MAX_REVIEWS_KEPT_PER_BRANCH])

    b_state["reviews"] = existing_reviews
    b_state["rating"] = details.get("rating")
    b_state["user_ratings_total"] = details.get("userRatingCount")
    b_state["google_maps_uri"] = details.get("googleMapsUri")
    b_state["last_synced"] = _now_iso()

    all_reviews = list(existing_reviews.values())
    last_review_time = max(
        (r["publish_time"] for r in all_reviews if r.get("publish_time")),
        default=None,
    )
    b_state["last_review_time"] = last_review_time

    low_rating_alerts = [
        r for r in new_reviews if (r.get("rating") or 0) <= LOW_RATING_THRESHOLD
    ]

    return {
        "rating": b_state["rating"],
        "user_ratings_total": b_state["user_ratings_total"],
        "google_maps_uri": b_state["google_maps_uri"],
        "new_reviews": new_reviews,
        "low_rating_alerts": low_rating_alerts,
        "last_review_time": last_review_time,
        "reviews_corpus": sorted(
            all_reviews, key=lambda r: r.get("publish_time") or "", reverse=True
        ),
    }
