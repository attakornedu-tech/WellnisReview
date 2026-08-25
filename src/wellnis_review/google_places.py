"""Thin wrapper around Google Places API (New) v1.

Docs: https://developers.google.com/maps/documentation/places/web-service/place-details
Note: Place Details returns at most 5 reviews per place — this is a hard limit
of the API (no pagination for reviews). By default Google picks those 5 by
"relevance", which is NOT the same as newest — a branch can easily have
reviews from days ago that rank as more "relevant" than something posted
yesterday, silently hiding genuinely new reviews from "รีวิวใหม่วันนี้". We pass
reviewsSort=NEWEST explicitly so the 5 returned are always the 5 most recently
published, matching what "ใหม่ที่สุด" shows in the Google Maps app itself.
"""
from __future__ import annotations

import requests

PLACES_BASE = "https://places.googleapis.com/v1"

DETAILS_FIELD_MASK = ",".join(
    [
        "id",
        "displayName",
        "rating",
        "userRatingCount",
        "googleMapsUri",
        "reviews.name",
        "reviews.rating",
        "reviews.text",
        "reviews.originalText",
        "reviews.publishTime",
        "reviews.relativePublishTimeDescription",
        "reviews.authorAttribution",
    ]
)

SEARCH_FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location"


class PlacesApiError(RuntimeError):
    pass


def get_place_details(api_key: str, place_id: str) -> dict:
    """Fetch current rating + latest (up to 5) reviews for a place."""
    url = f"{PLACES_BASE}/places/{place_id}"
    resp = requests.get(
        url,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": DETAILS_FIELD_MASK,
        },
        params={
            # languageCode=th: ask Google to return reviews.text (and displayName)
            # translated to Thai instead of its default (English). reviews.originalText
            # is unaffected — it always carries the review's original, untranslated language.
            "languageCode": "th",
            # reviewsSort=NEWEST: return the 5 most recently published reviews, not the
            # 5 Google considers most "relevant" (its default) — see module docstring.
            "reviewsSort": "NEWEST",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise PlacesApiError(f"Place Details failed ({resp.status_code}): {resp.text[:500]}")
    return resp.json()


def search_text(
    api_key: str,
    query: str,
    lat: float | None = None,
    lng: float | None = None,
    radius_m: float = 3000.0,
) -> list[dict]:
    """Text Search — used once by scripts/resolve_place_ids.py to find place_id."""
    body: dict = {"textQuery": query}
    if lat is not None and lng is not None:
        body["locationBias"] = {
            "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": radius_m}
        }
    resp = requests.post(
        f"{PLACES_BASE}/places:searchText",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": SEARCH_FIELD_MASK,
        },
        json=body,
        timeout=30,
    )
    if resp.status_code != 200:
        raise PlacesApiError(f"Text Search failed ({resp.status_code}): {resp.text[:500]}")
    return resp.json().get("places", [])
