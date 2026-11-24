"""End-to-End Pre-Deployment Smoke Test (Live Data & Cloud Readiness)."""
import json
import os
import sys

# Ensure backend and harness are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.api import app, TAIPEI_6P_PRESET
from harness.checker import check_plan
from harness.venues_live import fetch_live_venues


def run_smoke_test():
    print("==================================================================")
    print("🚀 STARTING PRE-DEPLOYMENT AUDIT & SMOKE TEST")
    print("==================================================================")

    client = TestClient(app)

    # 1. Health check & Live Probe
    print("\n[1/5] Testing /api/health with Live Probe...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    health = res.json()
    print(f"  ✓ Health Status: {health['status']}")
    print(f"  ✓ Data Mode: {health['data_mode']}")
    print(f"  ✓ Providers: {json.dumps(health['providers'], ensure_ascii=False, indent=4)}")

    # 2. Venues Live Search (Taipei & arbitrary city Kyoto)
    print("\n[2/5] Testing Venues API & Global Real Venue Search...")
    res_taipei = client.get("/api/venues?city=taipei")
    assert res_taipei.status_code == 200
    taipei_venues = res_taipei.json()
    assert len(taipei_venues) >= 20
    print(f"  ✓ Taipei Venues Loaded: {len(taipei_venues)} venues (Snapshot + Coordinates)")

    res_kyoto = client.get("/api/venues?city=kyoto")
    assert res_kyoto.status_code == 200
    kyoto_venues = res_kyoto.json()
    assert len(kyoto_venues) > 0
    print(f"  ✓ Global City (Kyoto) Loaded via Live OSM/Nominatim: {len(kyoto_venues)} venues")
    first_kyoto = next(iter(kyoto_venues.values()))
    print(f"    Sample: {first_kyoto['name']} (lat: {first_kyoto['lat']}, lon: {first_kyoto['lon']}, cost: {first_kyoto['cost']})")

    # 3. SSE Plan Streaming Endpoint
    print("\n[3/5] Testing POST /api/plan/stream (SSE Multi-Agent Generation)...")
    stream_res = client.post(
        "/api/plan/stream",
        json={"user_request": "Plan trip", "setup": TAIPEI_6P_PRESET["setup"]}
    )
    assert stream_res.status_code == 200
    lines = stream_res.text.strip().split("\n\n")
    events = [json.loads(line[6:]) for line in lines if line.startswith("data: ")]
    final_event = next(e for e in events if e.get("event") == "finished")
    plan = final_event["plan"]
    assert plan["feasible"] is True
    violations = check_plan(plan, TAIPEI_6P_PRESET["setup"])
    assert len(violations) == 0, f"Plan has violations: {violations}"
    print(f"  ✓ SSE Streaming Streamed {len(events)} steps successfully.")
    print(f"  ✓ Final Plan Items: {len(plan['itinerary'])} items, Checker Violations: 0")

    # 4. Emergency Replan & Localized Diff
    print("\n[4/5] Testing POST /api/plan/replan (Emergency 14:00 85% Rain Spike)...")
    replan_res = client.post(
        "/api/plan/replan",
        json={
            "current_plan": plan,
            "setup": TAIPEI_6P_PRESET["setup"],
            "event": {"type": "rain_spike", "time": "14:00", "rain_prob": 85.0}
        }
    )
    assert replan_res.status_code == 200
    replan_data = replan_res.json()
    diff = replan_data["diff"]
    updated_plan = replan_data["updated_plan"]
    print(f"  ✓ Diff Computed: modified={diff['modified_count']}, unaffected={diff['unaffected_count']}")
    assert diff["unaffected_count"] >= 10
    assert diff["modified_count"] >= 1

    # Verify updated plan with modified rainy weather
    repaired_setup = json.loads(json.dumps(TAIPEI_6P_PRESET["setup"]))
    weather = repaired_setup.get("weather", {})
    for h in range(14, 18):
        weather[str(h)] = 0.85
    repaired_setup["weather"] = weather
    replan_violations = check_plan(updated_plan, repaired_setup)
    assert len(replan_violations) == 0, f"Replan violations: {replan_violations}"
    print("  ✓ Localized Replan Plan Checker Violations: 0")

    # 5. Cloud Deployment Files Verification
    print("\n[5/5] Checking Dockerfile and Environment Templates...")
    assert os.path.exists("Dockerfile"), "Dockerfile missing"
    assert os.path.exists(".env.example"), ".env.example missing"
    assert os.path.exists("frontend/.env.example"), "frontend/.env.example missing"
    assert os.path.exists("requirements.txt"), "requirements.txt missing"
    print("  ✓ Dockerfile, requirements.txt, and .env.example templates verified.")

    print("\n==================================================================")
    print("🎉 ALL PRE-DEPLOYMENT SMOKE TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================")


if __name__ == "__main__":
    run_smoke_test()
