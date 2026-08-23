#!/usr/bin/env python3
"""One-time helper: resolve each branch's Google `place_id` from its
maps.app.goo.gl short link, and write it into branches.json.

Why this is separate from the daily job: Places API (New) has no "look up by
share link" endpoint, so we (1) follow the short link's redirect to get the
full Google Maps URL, which usually contains the branch name and lat/lng,
then (2) call Places API Text Search biased to that location to find the
matching place_id.

Usage:
    python -m scripts.resolve_place_ids               # interactive — confirm each match
    python -m scripts.resolve_place_ids --yes          # non-interactive — auto-pick best match
    python -m scripts.resolve_place_ids --only bang_pu # just one branch

Requires: GOOGLE_MAPS_API_KEY in the environment. Needs real internet access —
run this locally or via the "resolve-place-ids" GitHub Action
(.github/workflows/resolve-place-ids.yml), not from a network-restricted sandbox.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnis_review import google_places  # noqa: E402
from wellnis_review.config import env, load_branches, save_branches  # noqa: E402

COORD_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
PLACE_NAME_RE = re.compile(r"/maps/place/([^/@]+)")


def resolve_redirect(short_url: str) -> str:
    resp = requests.get(short_url, allow_redirects=True, timeout=20)
    return resp.url


def parse_expanded_url(url: str) -> tuple[str | None, float | None, float | None]:
    name = None
    m = PLACE_NAME_RE.search(url)
    if m:
        name = unquote(m.group(1)).replace("+", " ")
    lat = lng = None
    m = COORD_RE.search(url)
    if m:
        lat, lng = float(m.group(1)), float(m.group(2))
    return name, lat, lng


def pick_candidate(candidates: list[dict], auto: bool) -> dict | None:
    if not candidates:
        return None
    if auto or len(candidates) == 1:
        return candidates[0]
    print("  พบหลายรายการ กรุณาเลือก:")
    for i, c in enumerate(candidates):
        name = c.get("displayName", {}).get("text", "?")
        addr = c.get("formattedAddress", "?")
        print(f"    [{i}] {name} — {addr}")
    print("    [s] ข้าม (เลือกเองทีหลังโดยแก้ branches.json)")
    choice = input("  เลือกหมายเลข: ").strip()
    if choice == "s" or not choice.isdigit():
        return None
    idx = int(choice)
    return candidates[idx] if 0 <= idx < len(candidates) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="auto-pick the top match, no prompts")
    parser.add_argument("--only", help="only resolve this branch key")
    args = parser.parse_args()

    api_key = env("GOOGLE_MAPS_API_KEY")
    branches = load_branches()
    resolved = []

    for branch in branches:
        if args.only and branch.key != args.only:
            resolved.append(branch)
            continue
        if branch.place_id:
            print(f"[skip] {branch.name}: already has place_id={branch.place_id}")
            resolved.append(branch)
            continue

        print(f"\n== {branch.name} ({branch.maps_url}) ==")
        try:
            expanded = resolve_redirect(branch.maps_url)
        except Exception as e:
            print(f"  ⚠️ เปิดลิงก์ไม่สำเร็จ: {e}")
            resolved.append(branch)
            continue

        name, lat, lng = parse_expanded_url(expanded)
        print(f"  ลิงก์เต็ม: {expanded}")
        print(f"  ชื่อที่พาร์สได้: {name!r}, พิกัด: {lat}, {lng}")

        query = f"{name or branch.name} เวลนิส คลินิก"
        try:
            candidates = google_places.search_text(api_key, query, lat, lng)
        except Exception as e:
            print(f"  ⚠️ ค้นหาผ่าน Places API ไม่สำเร็จ: {e}")
            resolved.append(branch)
            continue

        chosen = pick_candidate(candidates, args.yes)
        if not chosen:
            print(f"  ⚠️ ไม่พบผลลัพธ์ที่ชัดเจนสำหรับ {branch.name} — ข้ามไว้ก่อน")
            resolved.append(branch)
            continue

        place_id = chosen["id"]
        disp_name = chosen.get("displayName", {}).get("text", "?")
        addr = chosen.get("formattedAddress", "?")
        print(f"  ✅ เลือก: {disp_name} — {addr}\n  place_id = {place_id}")

        from dataclasses import replace

        resolved.append(replace(branch, place_id=place_id))

    save_branches(resolved)
    print("\nบันทึกลง branches.json แล้ว — ตรวจสอบให้แน่ใจว่าที่อยู่ตรงกับแต่ละสาขาก่อนใช้งานจริง")
    return 0


if __name__ == "__main__":
    sys.exit(main())
