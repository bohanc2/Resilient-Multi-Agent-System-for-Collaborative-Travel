"""Proposed system: LangGraph hierarchical supervisor + 3 sub-agents + deterministic checker,
with at most 3 localized replans (proposal section 5).

    START -> base_planner -> checker --pass--> END
                               |fail
                               v
                          supervisor --(group_sync | contingency | base_planner)--> checker ...
                               |-- declare_infeasible --> END
                               |-- submit_best (only after 3 replans) --> END
"""
from __future__ import annotations

import json
import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .llm import LLM, Recorder, tool_span
from .schemas import ItineraryItem, PlanOutput, SupervisorDecision
from .tools import RULES, TOOL_SCHEMAS, TripTools, public_setup

MAX_REPLANS = 3
MAX_WORKER_STEPS = 15
MAX_LLM_CALLS = 40

ROLES = {
    "base_planner": "You are the BASE PLANNER sub-agent. Draft the full itinerary: place the locked bookings first, "
                    "then fill each person's day around them. Keep people together when their interests and limits "
                    "allow; split into sub-groups when they diverge. Use batch tools: `get_travel_matrix` to fetch "
                    "all pairwise travel times at once, and `search_candidate_venues` to directly query top-5 candidates. "
                    "When done, call propose_plan.",
    "group_sync": "You are the GROUP SYNC sub-agent. Fix how the group splits and regroups: choose sub-groups by "
                  "interests, walk limits and budget, and align timing so every sub-group reaches each shared booking "
                  "within the allowed arrival gap (you may extend a visit's end time, within opening hours, so a "
                  "group leaves later). Use `get_travel_matrix` to check travel times for all sub-groups in one call. "
                  "Change only the items involved in the reported problems. When done, call propose_plan with the complete plan.",
    "contingency": "You are the CONTINGENCY sub-agent. Fix weather problems: replace outdoor items that overlap rainy "
                   "hours with indoor venues close by (prefer <= 15 min travel) that still fit the person's interests, "
                   "limits and timing. Use `search_candidate_venues(indoor_only=True)` and `get_travel_matrix` to batch find "
                   "replacements. Keep every unaffected item unchanged. When done, call propose_plan with the complete plan.",
}

SUPERVISOR = """You are the SUPERVISOR of a travel-planning team (sub-agents: base_planner = full redraft,
group_sync = split/regroup/timing fixes, contingency = rain fixes). The deterministic checker found problems
with the current plan. Choose ONE next step and give that sub-agent a short, specific instruction based on the checker violations.
Prefer a localized repair (group_sync or contingency) over a full redraft.
CRITICAL OVER-REFUSAL BAN:
You are strictly forbidden from choosing declare_infeasible unless an external tool or the deterministic solver explicitly returned "MATHEMATICALLY_INFEASIBLE".
You must never assume a request is impossible just because previous repair attempts had violations or worker budget was exhausted.
- If violations mention arrival gap, regroup, split, walk limits, or budget -> route to "group_sync".
- If violations mention rain, weather, or outdoor venue -> route to "contingency".
- Otherwise -> route to "base_planner" with specific guidance.
Answer JSON only: {"next": "group_sync"|"contingency"|"base_planner"|"declare_infeasible", "instruction": "...",
"reason": "..."}"""

SUPERVISOR_FINAL = """You are the SUPERVISOR. The replan budget is used up and the checker still reports problems.
Decide: ONLY if the deterministic solver or tools explicitly confirmed MATHEMATICALLY_INFEASIBLE, answer declare_infeasible.
Otherwise, you MUST answer submit_best to submit the best available plan.
Answer JSON only: {"next": "submit_best"|"declare_infeasible", "reason": "..."}"""


class State(TypedDict, total=False):
    plan: dict
    violations: list
    replans: int
    next: str
    instruction: str
    reason: str
    status: str
    log: list
    best_plan: dict
    best_violations_count: int


def _parse_json(text: str):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _validate_and_format_plan(raw: dict, task_setup: dict | None = None) -> dict:
    try:
        obj = PlanOutput.model_validate(raw)
        return obj.model_dump()
    except Exception:
        if isinstance(raw, dict) and "itinerary" in raw:
            items = []
            default_members = [t["name"] for t in (task_setup or {}).get("travelers", [])]
            for it in raw.get("itinerary", []):
                if isinstance(it, dict) and "venue_id" in it and "start" in it and "end" in it:
                    try:
                        validated_item = ItineraryItem(
                            venue_id=str(it["venue_id"]),
                            start=str(it["start"]),
                            end=str(it["end"]),
                            members=[str(m) for m in it.get("members", []) or default_members]
                        )
                        items.append(validated_item.model_dump())
                    except Exception:
                        items.append({
                            "venue_id": str(it["venue_id"]),
                            "start": str(it["start"]),
                            "end": str(it["end"]),
                            "members": [str(m) for m in it.get("members", []) or default_members]
                        })
            return {
                "feasible": bool(raw.get("feasible", True)),
                "reason": str(raw.get("reason", "")),
                "itinerary": items,
                "status": "VALIDATED_WITH_REPAIR"
            }
        return raw


class TravelAgent:
    def __init__(self, supervisor_llm: LLM, worker_llm: LLM):
        self.sup = supervisor_llm
        self.worker = worker_llm

    # ---- one ReAct sub-agent ----
    def _run_worker(self, role, task, tools: TripTools, rec: Recorder, state: State) -> dict:
        ctx = {"request": task["user"], "details": public_setup(task["setup"])}
        if state.get("plan"):
            ctx["current_plan"] = state["plan"]
            ctx["checker_violations"] = state.get("violations", [])
            ctx["supervisor_instruction"] = state.get("instruction", "")
        msgs = [{"role": "system", "content": RULES + "\n\n" + ROLES[role] +
                 "\nWhen done, call propose_plan with the complete plan (all items, not only the changed ones)."},
                {"role": "user", "content": json.dumps(ctx, ensure_ascii=False)}]
        nudged = False
        collected_candidates = []

        for step in range(MAX_WORKER_STEPS):
            if rec.llm_calls >= MAX_LLM_CALLS:
                break

            remaining = MAX_WORKER_STEPS - step
            if remaining <= 2:
                msgs.append({
                    "role": "system",
                    "content": f"[CRITICAL WARNING] Remaining {remaining} step(s): you MUST immediately call propose_plan with your complete best feasible plan!"
                })
            if remaining == 1:
                msgs.append({"role": "user", "content": "FINAL STEP: Call propose_plan right now with your complete plan JSON."})

            m = self.worker.chat(rec, msgs, node=role, tools=TOOL_SCHEMAS)
            am = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                am["tool_calls"] = []
                for c in m.tool_calls:
                    tc = {"id": c.id, "type": "function",
                          "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    extra = (getattr(c, "model_extra", None) or {}).get("extra_content")
                    if extra:  # Gemini 3 thought_signature must be echoed back, else HTTP 400
                        tc["extra_content"] = extra
                    am["tool_calls"].append(tc)
            msgs.append(am)

            if not m.tool_calls:
                plan = _parse_json(m.content or "")
                if plan and "itinerary" in plan:
                    return _validate_and_format_plan(plan, task["setup"])
                if nudged:
                    break
                nudged = True
                msgs.append({"role": "user", "content": "Call propose_plan with the complete plan JSON."})
                continue

            proposed = None
            for c in m.tool_calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if c.function.name == "propose_plan":
                    proposed = args.get("plan", args)
                    out = {"ok": True}
                    tool_span(rec, role, "propose_plan", args, lambda: out)
                else:
                    out = tool_span(rec, role, c.function.name, args,
                                    lambda n=c.function.name, a=args: tools.call(n, a))
                    if c.function.name in ("search_candidate_venues", "list_venues", "get_venue"):
                        if isinstance(out, list):
                            collected_candidates.extend(out[:5])
                        elif isinstance(out, dict) and "id" in out:
                            collected_candidates.append(out)
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(out, ensure_ascii=False)})

            if proposed is not None:
                return _validate_and_format_plan(proposed, task["setup"])

        # Step budget exhausted without propose_plan: NO silent fallback!
        return {
            "feasible": False,
            "status": "WORKER_BUDGET_EXHAUSTED",
            "reason": f"Worker {role} budget exhausted ({MAX_WORKER_STEPS} steps) without calling propose_plan",
            "collected_candidates": collected_candidates[:10],
            "itinerary": []
        }

    def run(self, task: dict) -> dict:
        rec = Recorder()
        tools = TripTools(task["setup"])

        def worker_node(role):
            def fn(state: State):
                plan = self._run_worker(role, task, tools, rec, state)
                st = plan.get("status", "OK")
                return {
                    "plan": plan,
                    "status": st,
                    "log": state.get("log", []) + [f"{role} finished (status: {st})"]
                }
            return fn

        def checker(state: State):
            plan = state["plan"]
            if plan.get("status") == "WORKER_BUDGET_EXHAUSTED":
                v = [f"WORKER_BUDGET_EXHAUSTED: {plan.get('reason', '')}. Candidates: {len(plan.get('collected_candidates', []))}"]
            elif plan.get("feasible") is False:
                v = [f"sub-agent says infeasible: {plan.get('reason', '')}"]
            else:
                v = tool_span(rec, "checker", "check_plan", {"items": len(plan.get("itinerary", []))},
                              lambda: tools.check(plan))

            best_p = state.get("best_plan")
            best_c = state.get("best_violations_count", 9999)
            if plan.get("itinerary") and len(v) < best_c:
                best_p = plan
                best_c = len(v)

            return {
                "violations": v,
                "best_plan": best_p,
                "best_violations_count": best_c,
                "log": state.get("log", []) + [f"checker: {len(v)} violations"]
            }

        def after_check(state: State):
            if not state["violations"]:
                return "pass"
            if rec.llm_calls >= MAX_LLM_CALLS:
                return "stop"
            return "supervisor"

        def supervisor(state: State):
            final = state.get("replans", 0) >= MAX_REPLANS
            ctx = {"request": task["user"], "details": public_setup(task["setup"]), "current_plan": state["plan"],
                   "checker_violations": state["violations"], "replans_used": state.get("replans", 0),
                   "replans_max": MAX_REPLANS}
            msgs = [{"role": "system", "content": RULES + "\n\n" + (SUPERVISOR_FINAL if final else SUPERVISOR)},
                    {"role": "user", "content": json.dumps(ctx, ensure_ascii=False)}]
            m = self.sup.chat(rec, msgs, node="supervisor", json_mode=True)
            d = _parse_json(m.content or "") or {}

            # Validate decision with Pydantic
            try:
                dec = SupervisorDecision.model_validate(d)
                nxt = dec.next
            except Exception:
                nxt = d.get("next")

            allowed = {"submit_best", "declare_infeasible"} if final else \
                {"group_sync", "contingency", "base_planner", "declare_infeasible"}
            if nxt not in allowed:
                nxt = "submit_best" if final else "base_planner"

            # Over-refusal guard: Only declare infeasible if deterministic solver confirms MATHEMATICALLY_INFEASIBLE
            if nxt == "declare_infeasible":
                feas = tools.check_feasibility()
                if feas.get("status") != "MATHEMATICALLY_INFEASIBLE":
                    # Task is feasible! Forbid refusal.
                    if final:
                        nxt = "submit_best"
                    else:
                        viols_str = " ".join(state.get("violations", []))
                        if any(k in viols_str for k in ["rain", "weather", "outdoor"]):
                            nxt = "contingency"
                        elif any(k in viols_str for k in ["gap", "regroup", "split", "walk", "budget", "members"]):
                            nxt = "group_sync"
                        else:
                            nxt = "base_planner"

            upd = {"next": nxt, "instruction": d.get("instruction", ""), "reason": d.get("reason", ""),
                   "log": state.get("log", []) + [f"supervisor -> {nxt}: {d.get('reason', '')}"]}
            if nxt in ROLES:
                upd["replans"] = state.get("replans", 0) + 1
            if nxt == "declare_infeasible":
                upd["plan"] = {"feasible": False, "reason": d.get("reason", "") or "; ".join(state["violations"][:3]),
                               "itinerary": []}
            elif nxt == "submit_best":
                curr = state.get("plan", {})
                if (curr.get("status") == "WORKER_BUDGET_EXHAUSTED" or not curr.get("itinerary")) and state.get("best_plan"):
                    upd["plan"] = state["best_plan"]

            return upd

        g = StateGraph(State)
        for r in ROLES:
            g.add_node(r, worker_node(r))
            g.add_edge(r, "checker")
        g.add_node("checker", checker)
        g.add_node("supervisor", supervisor)
        g.add_edge(START, "base_planner")
        g.add_conditional_edges("checker", after_check, {"pass": END, "stop": END, "supervisor": "supervisor"})
        g.add_conditional_edges("supervisor", lambda s: s["next"],
                                {**{r: r for r in ROLES}, "declare_infeasible": END, "submit_best": END})
        app = g.compile()
        error = None
        try:
            final = app.invoke({"replans": 0, "log": [], "best_violations_count": 9999}, {"recursion_limit": 50})
        except Exception as e:  # keep the run; it is graded as a failure
            error = repr(e)
            final = {}

        plan = final.get("plan")
        if (plan is None or plan.get("status") == "WORKER_BUDGET_EXHAUSTED") and final.get("best_plan"):
            plan = final.get("best_plan")

        return {"plan": plan, "turns": rec.llm_calls, "tool_calls": rec.tool_calls,
                "input_tokens": rec.input_tokens, "output_tokens": rec.output_tokens, "tokens": rec.total_tokens,
                "replans": final.get("replans", 0), "log": final.get("log", []), "spans": rec.spans, "error": error}
