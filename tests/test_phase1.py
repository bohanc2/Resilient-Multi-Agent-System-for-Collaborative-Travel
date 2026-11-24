"""Unit tests verifying Phase 1 requirements:
1. Batch & domain-specific tools (get_travel_matrix, search_candidate_venues, check_feasibility)
2. Worker step budget, warning injection, and budget exhaustion (no silent fallback)
3. Supervisor over-refusal prevention
4. Structured outputs / Pydantic schema validation
"""
import pytest
from harness.tools import TripTools
from harness.schemas import ItineraryItem, PlanOutput, SupervisorDecision
from harness.agent import TravelAgent, ROLES, MAX_WORKER_STEPS
from harness.checker import check_plan


def test_batch_tools():
    setup = {
        "city": "taipei",
        "weekday": "Sat",
        "travelers": [{"name": "Ann", "budget": 1000, "interests": ["cafe"], "max_walk": 2}]
    }
    tools = TripTools(setup)

    # 1. get_travel_matrix
    origins = ["hotel_ximen", "cafe_simple_kaffa"]
    destinations = ["din_tai_fung_101", "taipei101_observatory"]
    mat = tools.get_travel_matrix(origins, destinations, mode="taxi")
    assert mat["mode"] == "taxi"
    assert "hotel_ximen" in mat["matrix"]
    assert "din_tai_fung_101" in mat["matrix"]["hotel_ximen"]
    assert isinstance(mat["matrix"]["hotel_ximen"]["din_tai_fung_101"], int)

    # 2. search_candidate_venues
    top_cafes = tools.search_candidate_venues(categories=["cafe"], max_cost=250, indoor_only=True)
    assert len(top_cafes) <= 5
    assert len(top_cafes) > 0
    for v in top_cafes:
        assert "cafe" in v["tags"]
        assert v["cost"] <= 250
        assert v["indoor"] is True

    # 3. check_feasibility
    feas = tools.check_feasibility()
    assert feas["status"] in ("FEASIBLE", "MATHEMATICALLY_INFEASIBLE")


def test_pydantic_schemas():
    # Valid itinerary item
    item = ItineraryItem(venue_id="cafe_simple_kaffa", start="10:00", end="11:30", members=["Ann"])
    assert item.start == "10:00"
    assert item.end == "11:30"

    # Invalid time should raise
    with pytest.raises(Exception):
        ItineraryItem(venue_id="v", start="25:00", end="11:00", members=["Ann"])

    # Plan output validation
    plan = PlanOutput(feasible=True, reason="ok", itinerary=[item])
    d = plan.model_dump()
    assert d["feasible"] is True
    assert len(d["itinerary"]) == 1

    # Supervisor decision
    dec = SupervisorDecision(next="group_sync", instruction="fix gap", reason="tight")
    assert dec.next == "group_sync"

    with pytest.raises(Exception):
        SupervisorDecision(next="invalid_role")


def test_worker_budget_exhaustion_no_silent_fallback():
    class DummyExhaustedLLM:
        def chat(self, rec, msgs, node, tools=None, json_mode=False):
            from types import SimpleNamespace as NS
            # Simulates worker calling tools repeatedly without propose_plan
            return NS(content="", tool_calls=[
                NS(id="t1", function=NS(name="weather", arguments="{}"), model_extra=None)
            ])

    from harness.llm import Recorder
    rec = Recorder()
    setup = {
        "city": "taipei",
        "weekday": "Sat",
        "travelers": [{"name": "Ann", "budget": 1000, "interests": ["cafe"], "max_walk": 2}]
    }
    task = {"user": "Plan a trip", "setup": setup}
    agent = TravelAgent(DummyExhaustedLLM(), DummyExhaustedLLM())
    tools = TripTools(setup)
    state = {
        "plan": {"feasible": True, "reason": "old plan", "itinerary": [{"venue_id": "old", "start": "09:00", "end": "10:00", "members": ["Ann"]}]}
    }

    result = agent._run_worker("group_sync", task, tools, rec, state)
    # MUST return WORKER_BUDGET_EXHAUSTED and NOT silently return state["plan"]!
    assert result.get("status") == "WORKER_BUDGET_EXHAUSTED"
    assert result.get("feasible") is False
    assert "budget exhausted" in result.get("reason", "").lower()


def test_supervisor_over_refusal_guard():
    import json
    from types import SimpleNamespace as NS

    class RefusalSupervisorLLM:
        def chat(self, rec, msgs, node, tools=None, json_mode=False):
            # Supervisor maliciously attempts declare_infeasible
            return NS(content=json.dumps({"next": "declare_infeasible", "reason": "I want to give up"}), tool_calls=None)

    class DummyWorkerLLM:
        def chat(self, rec, msgs, node, tools=None, json_mode=False):
            return NS(content="", tool_calls=[])

    setup = {
        "city": "taipei",
        "weekday": "Sat",
        "travelers": [{"name": "Ann", "budget": 1000, "interests": ["cafe"], "max_walk": 2}]
    }
    task = {"user": "Plan a trip", "setup": setup}
    agent = TravelAgent(RefusalSupervisorLLM(), DummyWorkerLLM())
    tools = TripTools(setup)
    # The setup is feasible:
    assert tools.check_feasibility()["status"] == "FEASIBLE"

    from harness.llm import Recorder
    rec = Recorder()

    # When supervisor runs on a feasible task:
    state = {
        "plan": {"feasible": True, "reason": "initial", "itinerary": []},
        "violations": ["cafe_simple_kaffa starts too early"],
        "replans": 0,
        "log": []
    }

    # Test supervisor node directly:
    # We can inspect supervisor node logic inside agent
    # By running supervisor logic on state
    # Let's extract supervisor logic or run graph
    res = agent.run(task)
    # Because task is mathematically feasible, supervisor must NOT declare infeasible!
    # Even though supervisor LLM returns 'declare_infeasible' every time, over-refusal guard blocks it!
    # It should not return feasible=False with "I want to give up"
    assert res["plan"].get("reason") != "I want to give up"


if __name__ == "__main__":
    test_batch_tools()
    test_pydantic_schemas()
    test_worker_budget_exhaustion_no_silent_fallback()
    test_supervisor_over_refusal_guard()
    print("All Phase 1 unit tests PASSED successfully!")
