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
from .tools import RULES, TOOL_SCHEMAS, TripTools, public_setup

MAX_REPLANS = 3
MAX_WORKER_STEPS = 10
MAX_LLM_CALLS = 40

ROLES = {
    "base_planner": "You are the BASE PLANNER sub-agent. Draft the full itinerary: place the locked bookings first, "
                    "then fill each person's day around them. Keep people together when their interests and limits "
                    "allow; split into sub-groups when they diverge. Use the tools for venues, hours, travel times "
                    "and weather; do not guess numbers.",
    "group_sync": "You are the GROUP SYNC sub-agent. Fix how the group splits and regroups: choose sub-groups by "
                  "interests, walk limits and budget, and align timing so every sub-group reaches each shared booking "
                  "within the allowed arrival gap (you may extend a visit's end time, within opening hours, so a "
                  "group leaves later). Change only the items involved in the reported problems.",
    "contingency": "You are the CONTINGENCY sub-agent. Fix weather problems: replace outdoor items that overlap rainy "
                   "hours with indoor venues close by (prefer <= 15 min travel) that still fit the person's interests, "
                   "limits and timing. Keep every unaffected item unchanged.",
}

SUPERVISOR = """You are the SUPERVISOR of a travel-planning team (sub-agents: base_planner = full redraft,
group_sync = split/regroup/timing fixes, contingency = rain fixes). The deterministic checker found problems
with the current plan. Choose ONE next step and give that sub-agent a short, specific instruction.
Prefer a localized repair (group_sync or contingency) over a full redraft.
Declare the request infeasible only if it truly cannot be satisfied (impossible locked bookings, a required venue
that is closed/unknown/unreachable, a budget below fixed costs, a hard requirement conflicting with a limit).
Answer JSON only: {"next": "group_sync"|"contingency"|"base_planner"|"declare_infeasible", "instruction": "...",
"reason": "..."}"""

SUPERVISOR_FINAL = """You are the SUPERVISOR. The replan budget is used up and the checker still reports problems.
Decide: if the problems show the request is impossible, answer declare_infeasible; otherwise submit the best plan.
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
        for _ in range(MAX_WORKER_STEPS):
            if rec.llm_calls >= MAX_LLM_CALLS:
                break
            m = self.worker.chat(rec, msgs, node=role, tools=TOOL_SCHEMAS)
            am = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                am["tool_calls"] = []
                for c in m.tool_calls:
                    tc = {"id": c.id, "type": "function",
                          "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    extra = (c.model_extra or {}).get("extra_content")
                    if extra:  # Gemini 3 thought_signature must be echoed back, else HTTP 400
                        tc["extra_content"] = extra
                    am["tool_calls"].append(tc)
            msgs.append(am)
            if not m.tool_calls:
                plan = _parse_json(m.content or "")
                if plan and "itinerary" in plan:
                    return plan
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
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(out, ensure_ascii=False)})
            if proposed is not None:
                return proposed
        return state.get("plan") or {"feasible": True, "reason": "sub-agent gave no plan", "itinerary": []}

    def run(self, task: dict) -> dict:
        rec = Recorder()
        tools = TripTools(task["setup"])

        def worker_node(role):
            def fn(state: State):
                plan = self._run_worker(role, task, tools, rec, state)
                return {"plan": plan, "log": state.get("log", []) + [f"{role} proposed plan"]}
            return fn

        def checker(state: State):
            plan = state["plan"]
            if plan.get("feasible") is False:
                v = [f"sub-agent says infeasible: {plan.get('reason', '')}"]
            else:
                v = tool_span(rec, "checker", "check_plan", {"items": len(plan.get("itinerary", []))},
                              lambda: tools.check(plan))
            return {"violations": v, "log": state.get("log", []) + [f"checker: {len(v)} violations"]}

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
            nxt = d.get("next")
            allowed = {"submit_best", "declare_infeasible"} if final else \
                {"group_sync", "contingency", "base_planner", "declare_infeasible"}
            if nxt not in allowed:
                nxt = "submit_best" if final else "base_planner"
            upd = {"next": nxt, "instruction": d.get("instruction", ""), "reason": d.get("reason", ""),
                   "log": state.get("log", []) + [f"supervisor -> {nxt}: {d.get('reason', '')}"]}
            if nxt in ROLES:
                upd["replans"] = state.get("replans", 0) + 1
            if nxt == "declare_infeasible":
                upd["plan"] = {"feasible": False, "reason": d.get("reason", "") or "; ".join(state["violations"][:3]),
                               "itinerary": []}
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
            final = app.invoke({"replans": 0, "log": []}, {"recursion_limit": 50})
        except Exception as e:  # keep the run; it is graded as a failure
            error = repr(e)
            final = {}
        plan = final.get("plan")
        return {"plan": plan, "turns": rec.llm_calls, "tool_calls": rec.tool_calls,
                "input_tokens": rec.input_tokens, "output_tokens": rec.output_tokens, "tokens": rec.total_tokens,
                "replans": final.get("replans", 0), "log": final.get("log", []), "spans": rec.spans, "error": error}
