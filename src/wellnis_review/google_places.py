"""Thin wrapper around Google Places API (New) v1.

Docs: https://developers.google.com/maps/documentation/places/web-service/place-details
Note: Place Details returns at most the 5 most recent reviews per place — this is
a hard limit of the API (no pagination for reviews). The daily sync script works
around this by diffing against previously-seen reviews and accumulating a local
history per branch (see state_store.py), so "จำนวนรีวิวใหม่" stays accurate as
long as a branch doesn't receive more than 5 new reviews in a single day.
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
        # languageCode=th: ask Google to return reviews.text (and displayName) translated
        # to Thai instead of its default (English). reviews.originalText is unaffected —
        # it always carries the review's original, untranslated language.
        params={"languageCode": "th"},
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
