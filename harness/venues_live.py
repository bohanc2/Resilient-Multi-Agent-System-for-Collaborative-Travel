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
_CITY_METADATA: Dict[str, Dict[str, Any]] = {}


def geocode_city(city: str) -> Optional[Dict[str, Any]]:
    """Geocode city to obtain coordinates and formatted display name using OpenStreetMap Nominatim."""
    city_norm = city.strip().lower()
    if city_norm in _CITY_METADATA:
        return _CITY_METADATA[city_norm]

    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(city)}&format=json&limit=1&addressdetails=1"
        req = urllib.request.Request(url, headers={"User-Agent": "AuraTravelPlanner/2.0 (Resilient-Multi-Agent)"})
        with urllib.request.urlopen(req, timeout=3.5) as r:
            res = json.load(r)
            if not res:
                return None
            item = res[0]
            lat = float(item["lat"])
            lon = float(item["lon"])
            addr = item.get("address", {})
            c_name = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or item.get("display_name", "").split(",")[0].strip()
            state = addr.get("state") or addr.get("province")
            country_code = addr.get("country_code", "").upper()

            clean_name = f"{c_name}, {state}" if state else (f"{c_name}, {country_code}" if country_code else c_name)

            meta = {
                "city": clean_name,
                "lat": lat,
                "lon": lon,
                "display_name": item.get("display_name", city)
            }
            _CITY_METADATA[city_norm] = meta
            return meta
    except Exception as e:
        logger.warning(f"Geocoding error for {city}: {e}")
        return None


def get_city_metadata(city: str) -> Optional[Dict[str, Any]]:
    return _CITY_METADATA.get(city.strip().lower())

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
            with urllib.request.urlopen(req, timeout=2.5) as r:
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


def fetch_from_osm_nominatim(city: str, limit: int = 20) -> Dict[str, Dict[str, Any]]:
    """Fetch real venues from OpenStreetMap Nominatim API across diverse interest categories."""
    venues: Dict[str, Dict[str, Any]] = {}

    # 1. Geocode city center
    geo = geocode_city(city)
    if not geo:
        logger.warning(f"OSM geocoding failed for {city}: completely unknown or invalid city")
        return {}

    center_lat = geo["lat"]
    center_lon = geo["lon"]
    clean_city = geo["city"]

    # 2. Query balanced categories (attractions, parks, hiking, museums, cafes, restaurants)
    categories = [
        (f"attractions in {city}", ["scenic", "culture"]),
        (f"parks in {city}", ["nature", "hiking", "scenic"]),
        (f"outdoor in {city}", ["hiking", "scenic", "nature"]),
        (f"museums in {city}", ["museum", "art"]),
        (f"cafes in {city}", ["cafe", "food"]),
        (f"restaurants in {city}", ["food", "dining"]),
    ]

    for q, default_tags in categories:
        if len(venues) >= limit:
            break
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=4&addressdetails=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AuraTravelPlanner/2.0 (Resilient-Multi-Agent)"})
            with urllib.request.urlopen(req, timeout=2.5) as r:
                results = json.load(r)
                for item in results:
                    disp_name = item.get("display_name", "")
                    name = disp_name.split(",")[0].strip()
                    if not name or len(name) < 2:
                        continue
                    vid = f"{city}_{_slugify(name)}"
                    if vid in venues:
                        continue
                    lat = float(item.get("lat", center_lat or 0.0))
                    lon = float(item.get("lon", center_lon or 0.0))
                    category = item.get("category", "")
                    osm_type = item.get("type", "")

                    is_indoor = not any(w in name.lower() or w in [category, osm_type] for w in ["park", "mountain", "trail", "beach", "garden", "viewpoint", "lake", "forest"])
                    walk_lvl = 3 if any(w in name.lower() for w in ["mountain", "trail", "peak", "hike"]) else (1 if not is_indoor else 0)

                    tags = list(default_tags)
                    if "museum" in name.lower() or osm_type == "museum":
                        tags = ["museum", "art"]
                    elif "cafe" in name.lower() or osm_type == "cafe":
                        tags = ["cafe", "food"]
                    elif "restaurant" in name.lower() or osm_type in ["restaurant", "fast_food"]:
                        tags = ["food", "dining"]
                    elif "park" in name.lower() or osm_type == "park":
                        tags = ["nature", "scenic"]
                    elif any(w in name.lower() for w in ["trail", "mountain", "hike"]):
                        tags = ["hiking", "scenic", "nature"]

                    cost = 25 if "dining" in tags or "food" in tags else (15 if "museum" in tags else (8 if "cafe" in tags else 0))

                    venues[vid] = {
                        "id": vid,
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "indoor": is_indoor,
                        "open": "09:00",
                        "close": "21:30",
                        "closed_days": [],
                        "min_minutes": 60,
                        "cost": cost,
                        "walk": walk_lvl,
                        "tags": tags,
                        "description": f"Real venue from OpenStreetMap in {clean_city} ({disp_name[:80]}...).",
                        "city": city.lower(),
                        "source": "osm_nominatim"
                    }
        except Exception as e:
            logger.warning(f"OSM Nominatim query error for {q}: {e}")

    # Always add central basecamp hotel using clean geocoded city name
    hotel_id = f"hotel_{_slugify(city)}"
    venues[hotel_id] = {
        "id": hotel_id,
        "name": f"Hotel ({clean_city})",
        "lat": center_lat,
        "lon": center_lon,
        "indoor": True,
        "open": "00:00",
        "close": "23:59",
        "closed_days": [],
        "min_minutes": 0,
        "cost": 0,
        "walk": 0,
        "tags": ["hotel", "lodging"],
        "description": f"Central basecamp accommodation in {clean_city}.",
        "city": city.lower(),
        "source": "generated_hotel"
    }

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

    if venues:
        _LIVE_VENUE_CACHE[city_norm] = venues

    return venues
