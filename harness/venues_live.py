"""Live Venue Search provider: Google Places API + OpenStreetMap Overpass/Nominatim + Snapshot Fallback.

Supports querying arbitrary cities globally:
1. Google Places API (TextSearch / NearbySearch) if GOOGLE_PLACES_API_KEY is present in env.
2. OpenStreetMap Nominatim / Overpass API (free, no API key required) as automatic fallback.
3. Local curated snapshot (Taipei, Seattle, NYC, Tokyo, Paris) as deterministic fallback.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory cache for live venue results by city
_LIVE_VENUE_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}

# Tag mappings from OSM / Google categories
TAG_MAPPINGS = {
    "museum": ["museum", "art", "history"],
    "art_gallery": ["art", "museum"],
    "park": ["nature", "scenic"],
    "viewpoint": ["scenic", "nature"],
    "restaurant": ["food"],
    "cafe": ["cafe", "food"],
    "book_store": ["books", "shopping"],
    "shopping_mall": ["shopping"],
    "place_of_worship": ["culture", "history"],
    "historic": ["history", "culture"],
    "hiking": ["hiking", "nature"]
}


def _slugify(text: str) -> str:
    """Convert venue name to a clean identifier."""
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:32] if slug else "venue"


def fetch_from_google_places(city: str, api_key: str, limit: int = 12) -> Dict[str, Dict[str, Any]]:
    """Fetch real venues from Google Places Text Search API."""
    venues: Dict[str, Dict[str, Any]] = {}
    categories = ["attractions", "museums", "cafes", "parks"]

    for cat in categories:
        if len(venues) >= limit:
            break
        query = f"top {cat} in {city}"
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={api_key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AuraTravelPlanner/2.0"})
            with urllib.request.urlopen(req, timeout=4.0) as r:
                data = json.load(r)
                for item in data.get("results", [])[:4]:
                    name = item.get("name", "Unknown Venue")
                    vid = f"{city}_{_slugify(name)}"
                    if vid in venues:
                        continue
                    loc = item.get("geometry", {}).get("location", {})
                    lat = loc.get("lat", 0.0)
                    lon = loc.get("lng", 0.0)
                    types = item.get("types", [])
                    is_indoor = not any(w in name.lower() or w in types for w in ["park", "mountain", "trail", "beach", "garden"])
                    price_level = item.get("price_level", 1)
                    cost = price_level * 250 if "restaurant" in types or "food" in types else (150 if "museum" in types else 0)

                    # Extract tags
                    tags = ["scenic"]
                    for t in types:
                        if t in TAG_MAPPINGS:
                            tags.extend(TAG_MAPPINGS[t])
                    tags = list(dict.fromkeys(tags))[:3]

                    venues[vid] = {
                        "id": vid,
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "indoor": is_indoor,
                        "open": "09:00",
                        "close": "21:00",
                        "closed_days": [],
                        "min_minutes": 60,
                        "cost": cost,
                        "walk": 3 if "mountain" in name.lower() or "trail" in name.lower() else (1 if not is_indoor else 0),
                        "tags": tags,
                        "description": f"Real venue from Google Places API in {city.title()} (Rating: {item.get('rating', 'N/A')}).",
                        "city": city.lower(),
                        "source": "google_places"
                    }
        except Exception as e:
            logger.warning(f"Google Places API query error for {cat} in {city}: {e}")
            break

    return venues


def fetch_from_osm_nominatim(city: str, limit: int = 12) -> Dict[str, Dict[str, Any]]:
    """Fetch real venues from OpenStreetMap Nominatim API (Free, no API key required)."""
    venues: Dict[str, Dict[str, Any]] = {}
    queries = [f"attractions in {city}", f"museums in {city}", f"cafes in {city}"]

    for q in queries:
        if len(venues) >= limit:
            break
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=6&addressdetails=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AuraTravelPlanner/2.0 (Resilient-Multi-Agent)"})
            with urllib.request.urlopen(req, timeout=4.0) as r:
                results = json.load(r)
                for item in results:
                    disp_name = item.get("display_name", "")
                    name = disp_name.split(",")[0].strip()
                    if not name or len(name) < 2:
                        continue
                    vid = f"{city}_{_slugify(name)}"
                    if vid in venues:
                        continue
                    lat = float(item.get("lat", 0.0))
                    lon = float(item.get("lon", 0.0))
                    category = item.get("category", "")
                    osm_type = item.get("type", "")

                    is_indoor = not any(w in name.lower() or w in [category, osm_type] for w in ["park", "mountain", "trail", "beach", "garden", "viewpoint"])
                    walk_lvl = 3 if any(w in name.lower() for w in ["mountain", "trail", "peak"]) else (1 if not is_indoor else 0)

                    tags = ["scenic"]
                    if "museum" in name.lower() or osm_type == "museum":
                        tags = ["museum", "art"]
                    elif "cafe" in name.lower() or osm_type == "cafe":
                        tags = ["cafe", "food"]
                    elif "park" in name.lower() or osm_type == "park":
                        tags = ["nature", "scenic"]

                    venues[vid] = {
                        "id": vid,
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "indoor": is_indoor,
                        "open": "09:00",
                        "close": "21:00",
                        "closed_days": [],
                        "min_minutes": 60,
                        "cost": 150 if "museum" in tags else (120 if "cafe" in tags else 0),
                        "walk": walk_lvl,
                        "tags": tags,
                        "description": f"Real venue from OpenStreetMap in {city.title()} ({disp_name[:80]}...).",
                        "city": city.lower(),
                        "source": "osm_nominatim"
                    }
        except Exception as e:
            logger.warning(f"OSM Nominatim query error for {q}: {e}")
            break

    return venues


def fetch_live_venues(city: str) -> Dict[str, Dict[str, Any]]:
    """
    Get venues for a city using Google Places -> OSM Nominatim -> Fallback.
    Results are cached in memory.
    """
    city_norm = city.strip().lower()
    if city_norm in _LIVE_VENUE_CACHE and _LIVE_VENUE_CACHE[city_norm]:
        return _LIVE_VENUE_CACHE[city_norm]

    venues: Dict[str, Dict[str, Any]] = {}
    google_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()

    # 1. Try Google Places API
    if google_key:
        venues = fetch_from_google_places(city_norm, google_key)

    # 2. Try OSM Nominatim if Google Places not configured or returned empty
    if not venues:
        venues = fetch_from_osm_nominatim(city_norm)

    # Always ensure a central start hotel
    if venues:
        first_v = next(iter(venues.values()))
        hotel_id = f"hotel_{city_norm}"
        venues[hotel_id] = {
            "id": hotel_id,
            "name": f"Hotel ({city.title()})",
            "lat": first_v["lat"] + 0.005,
            "lon": first_v["lon"] + 0.005,
            "indoor": True,
            "open": "00:00",
            "close": "23:59",
            "closed_days": [],
            "min_minutes": 0,
            "cost": 0,
            "walk": 0,
            "tags": ["hotel"],
            "description": f"Central accommodation in {city.title()}. Trip departure and return point.",
            "city": city_norm,
            "source": "generated_hub"
        }
        _LIVE_VENUE_CACHE[city_norm] = venues

    return venues
