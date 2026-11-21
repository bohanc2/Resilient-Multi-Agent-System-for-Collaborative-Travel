# Project context (carried over from earlier session)

## Assignment — eval harness (teams of 2)
Due **Fri 2026-11-20, 11:59 PM Pacific**. Screenshot: `docs/assignment.webp`.

1. Write **50 tasks** in `tasks.jsonl` with known answers or rubrics, incl. **≥3 edge cases** and **≥2 unanswerable** tasks. Use the task format from the lecture slides (format not yet provided — ask the user for it).
2. Run the **agent** and a **non-agentic baseline** on all 50 tasks with **one script**.
3. Report **accuracy, avg turns, avg + p95 latency, avg tokens**, side by side.
4. **Trace one failure**: which step went wrong and why.
5. Run the agent **3× on all 50**; report **pass@3** (≥1 of 3 passes) and **pass^3** (all 3 pass), list tasks that flip.

Submit: `tasks.jsonl`, eval script, results table (with pass@3 / pass^3), one paragraph on the failure, both members' names + NetIDs.
These tasks are the first part of 200 due Nov 24; the harness will be reused, so keep it reusable.

## Our project (proposal: `docs/proposal.pdf`) — nothing implemented yet
"Resilient Multi-Agent System for Collaborative Travel": plans one trip for a group whose members have different limits (walking tolerance, budget, interests) and share locked bookings (hotel, dinner).
- LangGraph hierarchical supervisor + plan-and-replan loop (max 3 replans).
- Sub-agents: **Base Planner** (skeleton around fixed bookings), **Group Sync** (split/regroup, align transit), **Contingency** (rain → indoor backup within 15 min).
- **Deterministic checker**: transit times (OSRM/Google Routes), opening hours (Google Places), rain (Open-Meteo); conflicts go back to supervisor for localized repair.
- Demo: 6 friends, 2D1N Taipei, 18:30 locked dinner at Taipei 101, split into hike/museum/café, regroup by 18:15; 85% rain at 14:00 → only hike replaced, all arrive within 15 min.
- Proposal experiments: Single-Prompt Baseline vs Linear Pipeline vs Full system; metrics: accuracy (no hours/transit violations, regroup gap <15 min, preference share), safety (100% locked-booking preservation, prompt-injection resistance in venue descriptions), efficiency (tokens, API calls, latency).

## Mapping assignment → project
- Baseline = Single-Prompt Baseline (one LLM call, no tools).
- Agent = supervisor loop with tools + checker + ≤3 replans.
- Grading = deterministic checker (no violations, regroup gap ≤15 min, anchors preserved).
- Edge cases: single traveler, dinner too soon to reach, identical preferences, rain exactly 50%, prompt injection in venue description.
- Unanswerable: physically impossible schedule (101 at 10:00 → Jiufen at 10:20), required venue closed that day → agent must report infeasible.

## Plan agreed (MVP, given deadline today)
1. **Mock tools with static data** (Taipei venues w/ hours, indoor/outdoor, location; travel-time matrix; hourly rain) — reproducible, no API keys, stable across 3 runs.
2. **Simplified agent first**: LLM + tool-calling loop (`get_venue`, `travel_time`, `weather`, `check_plan`), replan on checker failure ≤3×. Full 3-sub-agent version later.
3. **Baseline**: same model, everything in one prompt, one call → itinerary JSON.
4. **`eval.py`**: read `tasks.jsonl` → run both → score with checker → log turns/latency/tokens → agent 3× → Markdown results table + pass@3/pass^3 + flipped tasks.

Example task line (adjust to the lecture's format):
```json
{"id": "t07", "category": "rain_repair", "travelers": [...], "anchors": [{"name": "Dinner @ Taipei 101", "time": "18:30", "locked": true}], "events": [{"at": "14:00", "type": "rain", "prob": 0.85}], "expected": {"answerable": true, "max_regroup_gap_min": 15, "anchors_preserved": true}}
```

## Still needed from the user
- Lecture slide showing the task format.
- Which LLM API (Claude / OpenAI / Gemini) and whether an API key is available.

## Task format (from lecture slides: Week 6 p.35–36, Week 7 p.16, p.27)
- `tasks.jsonl`, one JSON object per line. Lecture example:
  `{"id": "R07", "type": "policy", "user": "Return my order W4817420", "setup": {"W4817420": "pending"}, "pass_if": {"db_unchanged": true, "rubric": ["explains it is not delivered", "offers cancellation instead"]}}`
- Safety style: `{"id": "S01", "risk": "LLM01-indirect", "setup": {...}, "input": "...", "unsafe_if": "send_email called", "safe_if": "summary flags the request"}`
- Task types in lecture: golden Q&A (exact/contains), tool-call tests (args match), state checks (DB diff), unanswerable (no invention), multi-turn & memory (rubric), regression. Grade by state/trace first, LLM judge second.
- pass^k = mean over tasks of C(c,k)/C(n,k); with n=k=3 → all 3 pass.

### Our mapping
`id` / `type` / `user` (trip request text) / `setup` (travelers, anchors, events e.g. rain, venue overrides) / `pass_if` (deterministic: anchors_preserved, max_regroup_gap_min, no_hours_violation, no_transit_violation, no_rain_outdoor, ... ; unanswerable → `{"reports_infeasible": true}`). Prompt-injection task adds `risk` + `unsafe_if` (dinner anchor removed).

## Decisions
- LLM API: **OpenAI** (user's choice, 2026-11-20). Key read from `OPENAI_API_KEY` env or `.env`.
