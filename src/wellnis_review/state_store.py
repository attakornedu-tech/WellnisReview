"""Persisted per-branch snapshot: latest rating/reviews + a daily trend log.

"New today" is defined by each review's actual publish date (Bangkok calendar
day), not by whether our system has seen it before — this avoids the
bootstrap problem where a branch's entire review history gets miscounted as
"new" the first time it's synced, and it naturally stops flagging an old
low-rating review once its day has passed. There is no cross-day dedup here
by design: Google always returns the same up-to-5 latest reviews per place,
so each day's fetch is simply re-classified against "today" fresh.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import LOW_RATING_THRESHOLD, STATE_FILE
from .timeutil import is_today_bkk


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
    """Merge a fresh Place Details fetch into state; return a per-branch report:

    {
        "rating": float | None,
        "user_ratings_total": int | None,
        "google_maps_uri": str | None,
        "reviews": [review, ...],             # up to 5 latest, newest first
        "today_reviews": [review, ...],        # subset published today (Bangkok day)
        "low_rating_alerts_today": [review, ...],  # subset of today_reviews, rating <= threshold
        "new_reviews_today": int,
        "last_review_time": str | None,        # newest publish_time among fetched reviews
        "last_review_relative": str,           # Google's localized "X ago" for that review
    }
    """
    branches = state.setdefault("branches", {})
    b_state = branches.setdefault(branch_key, {})

    reviews = [parse_review(r) for r in details.get("reviews", [])]
    reviews.sort(key=lambda r: r.get("publish_time") or "", reverse=True)

    today_reviews = [
        r for r in reviews if r.get("publish_time") and is_today_bkk(r["publish_time"])
    ]
    low_rating_alerts_today = [
        r for r in today_reviews if (r.get("rating") or 0) <= LOW_RATING_THRESHOLD
    ]

    b_state["rating"] = details.get("rating")
    b_state["user_ratings_total"] = details.get("userRatingCount")
    b_state["google_maps_uri"] = details.get("googleMapsUri")
    b_state["last_synced"] = _now_iso()
    b_state["last_review_time"] = reviews[0]["publish_time"] if reviews else None
    b_state["last_review_relative"] = reviews[0]["relative_time"] if reviews else ""
    b_state["recent_reviews"] = reviews

    return {
        "rating": b_state["rating"],
        "user_ratings_total": b_state["user_ratings_total"],
        "google_maps_uri": b_state["google_maps_uri"],
        "reviews": reviews,
        "today_reviews": today_reviews,
        "low_rating_alerts_today": low_rating_alerts_today,
        "new_reviews_today": len(today_reviews),
        "last_review_time": b_state["last_review_time"],
        "last_review_relative": b_state["last_review_relative"],
    }
