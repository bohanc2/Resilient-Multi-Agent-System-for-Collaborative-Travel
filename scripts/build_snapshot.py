"""Freeze real travel times into snapshot/travel_matrix.json (run once; eval then uses the frozen file).

Source: OSRM public server (OpenStreetMap road network), driving profile, one /table request.
Door-to-door minutes = ceil(osrm_seconds / 60 * TRAFFIC_FACTOR + PICKUP_MIN)  (taxi / ride-hail model).
"""
import datetime
import json
import math
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from harness.data import VENUES  # noqa: E402

TRAFFIC_FACTOR = 1.3   # Taipei urban traffic vs. OSRM free-flow
PICKUP_MIN = 5         # waiting for the car + walking to the entrance

ids = list(VENUES)
coords = ";".join(f"{VENUES[i]['lon']},{VENUES[i]['lat']}" for i in ids)
url = f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration,distance"
with urllib.request.urlopen(url, timeout=60) as r:
    data = json.load(r)
assert data["code"] == "Ok", data
minutes = {a: {b: (0 if a == b else math.ceil(data["durations"][i][j] / 60 * TRAFFIC_FACTOR + PICKUP_MIN))
               for j, b in enumerate(ids)} for i, a in enumerate(ids)}
km = {a: {b: round(data["distances"][i][j] / 1000, 2) for j, b in enumerate(ids)} for i, a in enumerate(ids)}
out = {"source": "OSRM router.project-osrm.org /table driving", "retrieved": datetime.date.today().isoformat(),
       "formula": f"ceil(duration_min * {TRAFFIC_FACTOR} + {PICKUP_MIN})", "minutes": minutes, "km": km}
p = pathlib.Path(__file__).resolve().parents[1] / "snapshot" / "travel_matrix.json"
p.write_text(json.dumps(out, indent=1))
print("wrote", p, "e.g. hotel->101:", minutes["hotel_ximen"]["din_tai_fung_101"],
      "min; 101->jiufen:", minutes["taipei101_observatory"]["jiufen"], "min")
