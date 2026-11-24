"""Live backend for the interactive demo (not used by eval, which must be reproducible).

Same signatures as the snapshot backend in data.py:
    travel_minutes(a, b, venues) -> int      # OSRM route, same taxi formula as the snapshot
    rain_by_hour(lat, lon, date) -> {hour: prob}   # Open-Meteo hourly precipitation_probability
"""
from __future__ import annotations

import json
import math
import urllib.request

TRAFFIC_FACTOR, PICKUP_MIN = 1.3, 5


def _get(url: str, timeout: float = 3.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def travel_minutes(a: str, b: str, venues: dict) -> int:
    if a == b:
        return 0
    va, vb = venues[a], venues[b]
    d = _get(f"https://router.project-osrm.org/route/v1/driving/{va['lon']},{va['lat']};{vb['lon']},{vb['lat']}"
             "?overview=false")
    return math.ceil(d["routes"][0]["duration"] / 60 * TRAFFIC_FACTOR + PICKUP_MIN)


def rain_by_hour(lat: float, lon: float, date: str) -> dict[int, float]:
    d = _get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
             f"&hourly=precipitation_probability&timezone=Asia%2FTaipei&start_date={date}&end_date={date}")
    return {int(t[11:13]): p / 100 for t, p in zip(d["hourly"]["time"], d["hourly"]["precipitation_probability"])}
