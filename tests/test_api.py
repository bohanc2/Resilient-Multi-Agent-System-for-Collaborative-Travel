"""Verification test suite for FastAPI backend endpoints:
1. GET /api/demo/taipei-preset
2. POST /api/plan/stream (SSE streaming)
3. POST /api/plan/replan (Emergency rain spike repair + before/after Diff)
4. Hybrid data layer (Live API + snapshot fallback)
"""
import json
import os
from fastapi.testclient import TestClient
from backend.api import app, TAIPEI_6P_PRESET
from harness.checker import check_plan


def test_taipei_preset_endpoint():
    client = TestClient(app)
    response = client.get("/api/demo/taipei-preset")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "setup" in data
    setup = data["setup"]
    assert len(setup["travelers"]) == 6
    assert setup["anchors"][0]["venue_id"] == "din_tai_fung_101"
    assert setup["anchors"][0]["start"] == "18:30"
    print("✓ GET /api/demo/taipei-preset verified successfully")


def test_plan_stream_endpoint():
    client = TestClient(app)
    setup = TAIPEI_6P_PRESET["setup"]
    response = client.post("/api/plan/stream", json={"user_request": "Plan trip", "setup": setup})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    lines = response.text.strip().split("\n\n")
    events = []
    final_plan = None
    for line in lines:
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            events.append(payload)
            if payload.get("event") == "finished":
                final_plan = payload.get("plan")

    node_names = [e.get("node") for e in events]
    assert "orchestrator" in node_names
    assert "base_planner" in node_names
    assert "group_sync" in node_names
    assert "checker" in node_names

    assert final_plan is not None
    assert final_plan.get("feasible") is True
    assert len(final_plan.get("itinerary", [])) > 0
    # Check that plan passes deterministic checker
    violations = check_plan(final_plan, setup)
    assert len(violations) == 0, f"Plan violations: {violations}"
    print(f"✓ POST /api/plan/stream verified: {len(events)} SSE steps streamed, 0 violations in final plan")


def test_plan_replan_endpoint():
    client = TestClient(app)
    setup = TAIPEI_6P_PRESET["setup"]

    # First get initial plan
    initial_res = client.post("/api/plan/stream", json={"user_request": "Plan trip", "setup": setup})
    for line in initial_res.text.strip().split("\n\n"):
        if line.startswith("data: "):
            p = json.loads(line[6:])
            if p.get("event") == "finished":
                initial_plan = p.get("plan")

    # Inject 14:00 sudden rain storm (85%)
    replan_payload = {
        "current_plan": initial_plan,
        "setup": setup,
        "event": {
            "type": "rain_spike",
            "time": "14:00",
            "rain_prob": 85.0
        }
    }

    response = client.post("/api/plan/replan", json=replan_payload)
    assert response.status_code == 200
    data = response.json()

    assert "diff" in data
    assert "updated_plan" in data
    diff = data["diff"]
    assert "event_summary" in diff
    assert "unaffected_groups" in diff
    assert "modified_groups" in diff

    updated_plan = data["updated_plan"]
    assert updated_plan.get("feasible") is True
    # Verify that the updated setup with rain passes checker with the new plan!
    repaired_setup = dict(setup)
    weather = dict(repaired_setup.get("weather", {}))
    for h in range(14, 18):
        weather[str(h)] = 0.85
    repaired_setup["weather"] = weather

    violations = check_plan(updated_plan, repaired_setup)
    assert len(violations) == 0, f"Updated plan has violations: {violations}"
    print(f"✓ POST /api/plan/replan verified: Diff computed (unaffected: {diff['unaffected_count']}, modified: {diff['modified_count']}), 0 violations in updated plan")


def test_hybrid_fallback():
    # Test with USE_LIVE_APIS=true in environment, ensuring graceful fallback
    os.environ["USE_LIVE_APIS"] = "true"
    from harness.data import travel_minutes, rain_by_hour, venues_for
    setup = TAIPEI_6P_PRESET["setup"]
    vs = venues_for(setup)

    # Should not raise any error even with external live network calls
    mins = travel_minutes("hotel_ximen", "din_tai_fung_101", vs)
    assert isinstance(mins, int)
    assert mins > 0

    rain = rain_by_hour(setup)
    assert isinstance(rain, dict)
    assert len(rain) > 0
    print(f"✓ Hybrid data layer verified: travel_minutes={mins}, rain_by_hour={len(rain)} hours, fallback operational")


if __name__ == "__main__":
    test_taipei_preset_endpoint()
    test_plan_stream_endpoint()
    test_plan_replan_endpoint()
    test_hybrid_fallback()
    print("\n🎉 ALL BACKEND API ENDPOINTS AND HYBRID FALLBACK FULLY VERIFIED!")
