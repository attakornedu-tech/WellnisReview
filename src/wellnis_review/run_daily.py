"""Daily orchestrator: fetch reviews for every branch, update local state,
send a Telegram digest, and refresh the dashboard data.

Run manually:  python -m wellnis_review.run_daily
Run in CI:     .github/workflows/daily-review-sync.yml (cron 14:00 UTC = 21:00 ICT)
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

from . import google_places, notify_telegram, state_store
from .build_dashboard import build_dashboard_data, write_dashboard_data
from .config import LOW_RATING_THRESHOLD, env, load_branches
from .timeutil import BANGKOK, fmt_dt_bkk, today_bkk


def _stars(rating: float | int | None) -> str:
    if rating is None:
        return "ยังไม่มีรีวิว"
    full = round(rating)
    return "⭐" * max(full, 0) + f" ({rating:.1f})"


def _esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _review_line(r: dict) -> str:
    snippet = (r.get("text") or "").strip().replace("\n", " ")
    if len(snippet) > 300:
        snippet = snippet[:300] + "…"
    marker = "⚠️ " if (r.get("rating") or 0) <= LOW_RATING_THRESHOLD else ""
    return (
        f"  {marker}{r.get('rating')}⭐ โดย {_esc(r.get('author'))}: "
        f"{_esc(snippet) if snippet else '(ไม่มีข้อความ)'}"
    )


def _branch_section(branch_name: str, maps_url: str, report: dict | None) -> str:
    lines = [f"🏥 <b>{_esc(branch_name)}</b>"]

    if report is None:
        lines.append("⚠️ ดึงข้อมูลไม่สำเร็จวันนี้ (ดู log ของ GitHub Action)")
        return "\n".join(lines)

    rating = report["rating"]
    total = report["user_ratings_total"]
    today_reviews = report["today_reviews"]
    low_alerts = report["low_rating_alerts_today"]

    if rating is None:
        lines.append("คะแนนรวม: ยังไม่มีรีวิว (อาจเป็นสาขาใหม่)")
    else:
        lines.append(f"คะแนนรวม: {_stars(rating)} จาก {total or 0} รีวิว")

    if today_reviews:
        lines.append(f"📝 รีวิวใหม่วันนี้: <b>{len(today_reviews)}</b> รายการ")
        for r in today_reviews:
            lines.append(_review_line(r))
        if low_alerts:
            lines.append(f'  ⚠️ มี {len(low_alerts)} รายการ ≤{LOW_RATING_THRESHOLD} ดาว — ต้องติดตามด่วน')
            lines.append(f'  🔗 <a href="{_esc(maps_url)}">เปิดดูใน Google Maps</a>')
    else:
        last_rel = report.get("last_review_relative") or ""
        last_time = report.get("last_review_time")
        if last_time:
            lines.append(
                f"📝 วันนี้ไม่มีรีวิวใหม่ — รีวิวล่าสุด {_esc(last_rel)} "
                f"({_esc(fmt_dt_bkk(last_time))})"
            )
        else:
            lines.append("📝 วันนี้ไม่มีรีวิวใหม่ — ยังไม่เคยมีรีวิวเลย")

    return "\n".join(lines)


def main() -> int:
    google_key = env("GOOGLE_MAPS_API_KEY")
    telegram_token = env("TELEGRAM_BOT_TOKEN", required=False)
    telegram_chat_id = env("TELEGRAM_CHAT_ID", required=False)
    send_telegram = bool(telegram_token and telegram_chat_id)
    if not send_telegram:
        print("::warning::TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set — skipping Telegram send")

    branches = load_branches()
    state = state_store.load_state()

    sections: list[str] = []
    dashboard_branches: list[dict] = []
    ok_count = 0
    today = today_bkk().isoformat()

    for branch in branches:
        if not branch.place_id:
            print(f"[skip] {branch.name}: no place_id yet — run scripts/resolve_place_ids.py")
            sections.append(
                f"🏥 <b>{_esc(branch.name)}</b>\n⚠️ ยังไม่ได้ผูก place_id "
                f"(รัน scripts/resolve_place_ids.py ก่อน)"
            )
            dashboard_branches.append(
                {
                    "key": branch.key,
                    "name": branch.name,
                    "maps_url": branch.maps_url,
                    "status": "no_place_id",
                }
            )
            continue

        try:
            details = google_places.get_place_details(google_key, branch.place_id)
            report = state_store.update_branch_state(state, branch.key, details)
        except Exception:
            traceback.print_exc()
            sections.append(
                f"🏥 <b>{_esc(branch.name)}</b>\n⚠️ ดึงข้อมูลไม่สำเร็จวันนี้ (ดู log)"
            )
            dashboard_branches.append(
                {
                    "key": branch.key,
                    "name": branch.name,
                    "maps_url": branch.maps_url,
                    "status": "fetch_error",
                }
            )
            continue

        ok_count += 1
        b_state = state["branches"][branch.key]

        sections.append(_branch_section(branch.name, branch.maps_url, report))

        # append/replace today's entry in a rolling daily log (max 60 days) for trend display
        log = b_state.setdefault("daily_log", [])
        log = [entry for entry in log if entry.get("date") != today]
        log.append(
            {
                "date": today,
                "new_reviews": report["new_reviews_today"],
                "rating": report["rating"],
                "user_ratings_total": report["user_ratings_total"],
            }
        )
        b_state["daily_log"] = sorted(log, key=lambda e: e["date"])[-60:]

        dashboard_branches.append(
            {
                "key": branch.key,
                "name": branch.name,
                "maps_url": branch.maps_url,
                "status": "ok",
                "rating": report["rating"],
                "user_ratings_total": report["user_ratings_total"],
                "new_reviews_today": report["new_reviews_today"],
                "today_reviews": [
                    {
                        "author": r.get("author"),
                        "rating": r.get("rating"),
                        "text": r.get("text"),
                        "publish_time": r.get("publish_time"),
                    }
                    for r in report["today_reviews"]
                ],
                "low_rating_alerts_today": [
                    {
                        "author": r.get("author"),
                        "rating": r.get("rating"),
                        "text": r.get("text"),
                        "publish_time": r.get("publish_time"),
                    }
                    for r in report["low_rating_alerts_today"]
                ],
                "last_review_time": report["last_review_time"],
                "last_review_relative": report["last_review_relative"],
                "recent_reviews": [
                    {
                        "author": r.get("author"),
                        "rating": r.get("rating"),
                        "text": r.get("text"),
                        "publish_time": r.get("publish_time"),
                    }
                    for r in report["reviews"]
                ],
                "daily_log": b_state["daily_log"],
                "last_synced": b_state.get("last_synced"),
            }
        )

    state_store.save_state(state)
    write_dashboard_data(build_dashboard_data(dashboard_branches))

    if send_telegram:
        header = (
            f"📊 <b>สรุปรีวิว Google Maps ทั้ง {len(branches)} สาขา</b>\n"
            f"🗓 {datetime.now(BANGKOK).strftime('%d/%m/%Y %H:%M น.')}\n"
        )
        digest = header + "\n\n" + "\n\n".join(sections)
        try:
            notify_telegram.send_message(telegram_token, telegram_chat_id, digest)
            print("Telegram digest sent.")
        except Exception:
            traceback.print_exc()
            print("::error::Failed to send Telegram digest")
            return 1

    print(f"Done: {ok_count}/{len(branches)} branches synced successfully.")
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
