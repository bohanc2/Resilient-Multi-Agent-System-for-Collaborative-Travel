"""Benchmark world for 5 cities (Taipei, Seattle, NYC, Tokyo, Paris): venues, travel times, weather.

Everything here is deterministic so repeated eval runs see identical tool outputs.
Venue coordinates/hours are real (hand-curated); travel times are a frozen OSRM snapshot of the real
road network; weather is injected per task scenario. harness/live.py has the live-API backend for demos.
"""
from __future__ import annotations

import copy
import json
import math
import pathlib

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# walk: 0 = flat / seated, 1 = light walking, 2 = lots of walking / stairs, 3 = real hike
# tags are matched against traveler interests
# time_suitability: "daytime" (09:00-18:00), "evening" (18:00-23:00), "any"
VENUES: dict[str, dict] = {
    "hotel_ximen": dict(name="Hotel (Ximending)", lat=25.0422, lon=121.5079, indoor=True,
                        open="00:00", close="23:59", closed_days=[], min_minutes=0, duration_mins=0, cost=0, walk=0,
                        tags=["hotel"], time_suitability="any", description="Your hotel. Start and end point of the day."),
    "din_tai_fung_101": dict(name="Din Tai Fung @ Taipei 101", lat=25.0336, lon=121.5648, indoor=True,
                             open="11:00", close="21:30", closed_days=[], min_minutes=60, duration_mins=75, cost=750, walk=0,
                             tags=["food", "dining", "restaurant"], time_suitability="any", description="World-renowned xiao long bao dumplings inside Taipei 101 mall."),
    "taipei101_observatory": dict(name="Taipei 101 Observatory", lat=25.0339, lon=121.5645, indoor=True,
                                  open="10:00", close="22:00", closed_days=[], min_minutes=60, duration_mins=75, cost=600, walk=0,
                                  tags=["scenic", "night_view"], time_suitability="evening", description="Indoor panoramic observation deck on the 89th floor."),
    "elephant_mountain": dict(name="Elephant Mountain Trail", lat=25.0273, lon=121.5764, indoor=False,
                              open="05:00", close="22:00", closed_days=[], min_minutes=75, duration_mins=90, cost=0, walk=3,
                              tags=["hiking", "scenic"], time_suitability="daytime", description="Steep stair trail offering iconic skyline views of Taipei 101."),
    "yangmingshan": dict(name="Yangmingshan Qixing Trail", lat=25.1559, lon=121.5482, indoor=False,
                         open="06:00", close="18:00", closed_days=[], min_minutes=90, duration_mins=120, cost=0, walk=3,
                         tags=["hiking", "nature"], time_suitability="daytime", description="Scenic volcanic peak trail in Yangmingshan National Park."),
    "national_palace_museum": dict(name="National Palace Museum", lat=25.1024, lon=121.5485, indoor=True,
                                   open="09:00", close="17:00", closed_days=["Mon"], min_minutes=90, duration_mins=120, cost=350,
                                   walk=1, tags=["museum", "history"], time_suitability="daytime",
                                   description="World-class imperial Chinese art and treasure collection. Closed Mondays."),
    "fine_arts_museum": dict(name="Taipei Fine Arts Museum", lat=25.0726, lon=121.5246, indoor=True,
                             open="09:30", close="17:30", closed_days=["Mon"], min_minutes=60, duration_mins=90, cost=30, walk=1,
                             tags=["museum", "art"], time_suitability="daytime", description="Modern and contemporary Taiwanese fine arts. Closed Mondays."),
    "moca_taipei": dict(name="MoCA Taipei", lat=25.0503, lon=121.5195, indoor=True,
                        open="10:00", close="18:00", closed_days=["Mon"], min_minutes=60, duration_mins=75, cost=100, walk=0,
                        tags=["museum", "art"], time_suitability="daytime", description="Contemporary art exhibitions in a historic brick schoolhouse. Closed Mondays."),
    "science_center": dict(name="National Taiwan Science Education Center", lat=25.0965, lon=121.5157,
                           indoor=True, open="09:00", close="17:00", closed_days=["Mon"], min_minutes=60, duration_mins=90,
                           cost=100, walk=1, tags=["museum", "science"], time_suitability="daytime",
                           description="Hands-on interactive science museum. Closed Mondays."),
    "beitou_museum": dict(name="Beitou Hot Spring Museum", lat=25.1366, lon=121.5070, indoor=True,
                          open="10:00", close="18:00", closed_days=["Mon"], min_minutes=45, duration_mins=60, cost=0, walk=1,
                          tags=["museum", "history"], time_suitability="daytime", description="Historic Japanese-era public bathhouse museum. Closed Mondays."),
    "cks_memorial": dict(name="Chiang Kai-shek Memorial Hall", lat=25.0346, lon=121.5218, indoor=False,
                         open="09:00", close="18:00", closed_days=[], min_minutes=45, duration_mins=60, cost=0, walk=1,
                         tags=["history", "culture"], time_suitability="daytime", description="Expansive ceremonial plaza and historic liberty square."),
    "longshan_temple": dict(name="Longshan Temple", lat=25.0372, lon=121.4999, indoor=False,
                            open="06:00", close="21:00", closed_days=[], min_minutes=30, duration_mins=45, cost=0, walk=0,
                            tags=["culture", "temple"], time_suitability="daytime", description="Historic landmark temple built in 1738 with ornate folk carvings."),
    "dihua_street": dict(name="Dihua Street (Dadaocheng)", lat=25.0558, lon=121.5100, indoor=False,
                         open="09:00", close="19:00", closed_days=[], min_minutes=60, duration_mins=75, cost=0, walk=1,
                         tags=["shopping", "culture"], time_suitability="daytime", description="Historic trade quarter lined with traditional tea shops and herbal medicine."),
    "huashan_park": dict(name="Huashan 1914 Creative Park", lat=25.0441, lon=121.5294, indoor=True,
                         open="10:00", close="20:00", closed_days=[], min_minutes=60, duration_mins=75, cost=0, walk=1,
                         tags=["art", "shopping"], time_suitability="daytime", description="Repurposed Japanese sake winery featuring boutique pop-ups and indie galleries."),
    "songshan_park": dict(name="Songshan Cultural and Creative Park", lat=25.0437, lon=121.5606, indoor=True,
                          open="09:00", close="18:00", closed_days=[], min_minutes=60, duration_mins=75, cost=0, walk=1,
                          tags=["art", "design"], time_suitability="daytime", description="Former heritage tobacco factory complex housing design showcases."),
    "eslite_songyan": dict(name="Eslite Spectrum Songyan", lat=25.0445, lon=121.5600, indoor=True,
                           open="00:00", close="23:59", closed_days=[], min_minutes=45, duration_mins=60, cost=0, walk=0,
                           tags=["shopping", "books", "culture", "design", "art"], time_suitability="any",
                           description="24-hour flagship bookstore, boutique crafts, and lifestyle cultural center."),
    "eslite_xinyi": dict(name="Eslite Spectrum Songyan", lat=25.0445, lon=121.5600, indoor=True,
                         open="00:00", close="23:59", closed_days=[], min_minutes=45, duration_mins=60, cost=0, walk=0,
                         tags=["shopping", "books", "culture", "design", "art"], time_suitability="any",
                         description="24-hour flagship bookstore (relocated to Songshan Cultural Park)."),
    "cafe_fujin": dict(name="Fujin Tree Cafe", lat=25.0601, lon=121.5579, indoor=True,
                       open="10:00", close="19:00", closed_days=[], min_minutes=45, duration_mins=60, cost=250, walk=0,
                       tags=["cafe", "food"], time_suitability="daytime", description="Tree-shaded boutique cafe on tranquil Fujin Street."),
    "cafe_simple_kaffa": dict(name="Simple Kaffa", lat=25.0443, lon=121.5300, indoor=True,
                              open="10:00", close="18:00", closed_days=[], min_minutes=45, duration_mins=60, cost=250, walk=0,
                              tags=["cafe", "food"], time_suitability="daytime", description="World Barista Champion flagship specialty coffee near Huashan."),
    "cafe_rufous": dict(name="Rufous Coffee", lat=25.0215, lon=121.5338, indoor=True,
                        open="13:00", close="21:00", closed_days=[], min_minutes=45, duration_mins=60, cost=250, walk=0,
                        tags=["cafe", "food"], time_suitability="any", description="Intimate artisanal pour-over coffee bar near Da'an Forest Park."),
    "yongkang_beef_noodles": dict(name="Yongkang Beef Noodles", lat=25.0329, lon=121.5298, indoor=True,
                                 open="11:00", close="20:30", closed_days=[], min_minutes=45, duration_mins=60, cost=320, walk=0,
                                 tags=["food", "lunch", "restaurant"], time_suitability="daytime",
                                 description="Legendary Sichuan-style spicy braised beef noodle soup in Yongkang foodie enclave."),
    "chun_shui_tang": dict(name="Chun Shui Tang Teahouse", lat=25.0390, lon=121.5200, indoor=True,
                           open="11:00", close="21:30", closed_days=[], min_minutes=45, duration_mins=60, cost=350, walk=0,
                           tags=["food", "lunch", "tea", "cafe"], time_suitability="any",
                           description="Inventor of pearl bubble milk tea serving Taiwanese classic lunch bento sets."),
    "maokong_gondola": dict(name="Maokong Gondola & Tea Houses", lat=24.9960, lon=121.5760, indoor=False,
                            open="09:00", close="21:00", closed_days=["Mon"], min_minutes=90, duration_mins=120, cost=120, walk=1,
                            tags=["scenic", "nature", "tea"], time_suitability="daytime",
                            description="Scenic glass-floor cable car ascending to hilltop tea plantations. Closed Mondays."),
    "shilin_market": dict(name="Shilin Night Market", lat=25.0880, lon=121.5241, indoor=False,
                          open="16:00", close="23:59", closed_days=[], min_minutes=60, duration_mins=90, cost=300, walk=1,
                          tags=["food", "shopping", "night_market"], time_suitability="evening", description="Taipei's most vibrant night market famous for Taiwanese street food."),
    "raohe_market": dict(name="Raohe Night Market", lat=25.0509, lon=121.5775, indoor=False,
                         open="17:00", close="23:00", closed_days=[], min_minutes=60, duration_mins=90, cost=300, walk=1,
                         tags=["food", "night_market"], time_suitability="evening", description="Bustling waterfront night market renowned for black pepper pork buns."),
    "jiufen": dict(name="Jiufen Old Street", lat=25.1092, lon=121.8452, indoor=False,
                   open="10:00", close="20:00", closed_days=[], min_minutes=90, duration_mins=120, cost=200, walk=2,
                   tags=["scenic", "nature", "hiking", "culture", "shopping"], time_suitability="daytime",
                   description="Atmospheric lantern-lit hillside heritage market overlooking the northeast coast."),
}

for _v in VENUES.values():
    _v["city"] = "taipei"
from .cities import CITY_INFO, city_venues  # noqa: E402

VENUES.update(city_venues())

RAIN_THRESHOLD = 0.5  # outdoor venue is NOT allowed during an hour whose rain prob is strictly > 0.5


def to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def venues_for(setup: dict) -> dict[str, dict]:
    """Venue table for a task, with per-task overrides (e.g. an injected description)."""
    city = setup.get("city", "taipei").lower()
    vs = {k: copy.deepcopy(v) for k, v in VENUES.items() if v.get("city") == city}
    
    # If city is not in snapshot or empty, dynamically fetch real venues from live providers
    if not vs:
        try:
            from .venues_live import fetch_live_venues
            live_vs = fetch_live_venues(city)
            if live_vs:
                vs = copy.deepcopy(live_vs)
        except Exception:
            vs = {}

    for vid, patch in (setup.get("venue_overrides") or {}).items():
        vs.setdefault(vid, {}).update(patch)
    return vs


import os

USE_LIVE_APIS = os.environ.get("USE_LIVE_APIS", "false").lower() in ("true", "1", "yes")

_MATRIX: dict[str, dict[str, int]] = {}
for _p in sorted((pathlib.Path(__file__).resolve().parents[1] / "snapshot").glob("travel_*.json")):
    _MATRIX.update(json.loads(_p.read_text())["minutes"])


def travel_minutes(a: str, b: str, venues: dict | None = None) -> int:
    """Door-to-door taxi minutes from the frozen OSRM snapshot or Live OSRM with snapshot fallback."""
    venues = venues or VENUES
    if a == b:
        return 0

    # 1. Instant O(1) in-memory snapshot matrix hit
    if a in _MATRIX and b in _MATRIX[a]:
        return _MATRIX[a][b]

    # 2. Live OSRM query for dynamic/new venues outside snapshot
    if USE_LIVE_APIS:
        try:
            from .live import travel_minutes as live_travel
            return live_travel(a, b, venues)
        except Exception:
            # Fallback to Euclidean estimation on timeout or error
            pass

    # 3. Safe fallback & coordinates lookup
    va = venues.get(a)
    vb = venues.get(b)
    if not va or not vb:
        # Cross-city residual or unknown venue: return reasonable default metropolitan transit time
        return 20

    lat1, lon1, lat2, lon2 = map(math.radians, (va["lat"], va["lon"], vb["lat"], vb["lon"]))
    d = 2 * 6371 * math.asin(math.sqrt(math.sin((lat2 - lat1) / 2) ** 2 +
                                       math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2))
    return math.ceil(8 + 3 * d)


def rain_by_hour(setup: dict) -> dict[int, float]:
    if USE_LIVE_APIS:
        try:
            import datetime
            from .cities import CITY_INFO
            from .live import rain_by_hour as live_rain
            city = setup.get("city", "taipei").lower()
            if city in CITY_INFO:
                lat = CITY_INFO[city]["lat"]
                lon = CITY_INFO[city]["lon"]
                date = setup.get("date", datetime.date.today().isoformat())
                return live_rain(lat, lon, date)
        except Exception:
            # Fallback to setup weather
            pass
    return {int(h): float(p) for h, p in (setup.get("weather") or {}).items()}


def rainy_hours(setup: dict) -> set[int]:
    return {h for h, p in rain_by_hour(setup).items() if p > RAIN_THRESHOLD}


def venue_summary(vid: str, v: dict) -> dict:
    return {"id": vid, "name": v["name"], "tags": v["tags"], "indoor": v["indoor"],
            "open": v["open"], "close": v["close"], "closed_days": v["closed_days"],
            "min_minutes": v["min_minutes"], "duration_mins": v.get("duration_mins", v.get("min_minutes", 60)),
            "time_suitability": v.get("time_suitability", "any"),
            "cost": v["cost"], "walk_level": v["walk"]}
