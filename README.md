# Resilient Multi-Agent System for Collaborative Travel: evaluation harness

Team: **Bo-Han Chang Chien (bohanc2)**, **Yu-Wei Huang (yuweih5)**

## 1. Project overview

Group travel planning is fragile. Friends or families traveling together often have different interests, personal budgets and stamina. The group also shares fixed, non-refundable commitments (**hard anchors**), such as a locked 18:30 dinner reservation.

Single-agent travel chatbots break under real group dynamics:
1. They assume one traveler and cannot manage parallel sub-group schedules.
2. They fail to synchronize **split and regroup** points, so people wait a long time.
3. When something changes (an afternoon downpour, a venue closure), they either fail silently or regenerate the whole itinerary. Regenerating can destroy locked reservations.

Our system adds:
- **Hierarchical coordination**: a LangGraph supervisor with Base Planner, Group Sync and Contingency sub-agents. It splits travelers into interest-aligned sub-groups and regroups them at shared bookings within a **maximum arrival gap of 15 minutes**.
- **Deterministic spatio-temporal checker**: rule-based checks on opening hours, transit times, rain, walking limits, budgets, anchors and regroup gaps. No LLM judge.
- **Localized replanning**: on a conflict, the supervisor routes the checker's errors to the right sub-agent. That sub-agent repairs only the affected part of the plan. The loop allows **at most 3 replans**.

## 2. Architecture

```
                       +------------------------------+
                       |  Task: travelers, anchors,   |
                       |  requirements (tasks.jsonl)  |
                       +---------------+--------------+
                                       |
            +--------------------------+--------------------------+
            |                                                     |
            v                                                     v
 +----------------------+                      +-------------------------------------+
 | Single-Prompt        |                      | Proposed system (LangGraph)         |
 | Baseline             |                      |                                     |
 | 1 LLM call, no tools,|                      |  Base Planner --tools--> plan       |
 | all data in prompt   |                      |        |                            |
 +----------+-----------+                      |        v                            |
            |                                  |  Checker --pass--> final plan       |
            |                                  |        | fail                       |
            |                                  |        v                            |
            |                                  |  Supervisor --> Group Sync          |
            |                                  |      (≤3x)  --> Contingency         |
            |                                  |             --> Base Planner        |
            |                                  |             --> declare infeasible  |
            |                                  +------------------+------------------+
            |                                                     |
            +--------------------------+--------------------------+
                                       v
                       +------------------------------+
                       |  Grader = same deterministic |
                       |  checker (harness/checker.py)|
                       +------------------------------+
```

Sub-agent tools: `list_venues`, `get_venue`, `travel_time`, `weather`, `propose_plan`.

## 3. Repository files

| File | Description |
|---|---|
| `tasks.jsonl` | 50 tasks in the lecture format (`id`, `type`, `user`, `setup`, `pass_if`), 10 per city. Answerable tasks carry a solver-verified `reference_answer`. |
| `eval.py` | One script. It runs the agent and the baseline on every task for N runs and grades them. It writes `results/<tag>/results.json`, `results/<tag>/results.md`, and one trace per run in `traces/<tag>/`. |
| `harness/agent.py` | Proposed system: LangGraph supervisor, 3 sub-agents, checker loop with ≤3 replans. |
| `harness/baseline.py` | Single-Prompt Baseline: one call with no tools and no feedback. It gets all tool data in the prompt. |
| `harness/checker.py` | Deterministic checker, used both as the grader and as the agent's checker node. |
| `harness/data.py`, `harness/cities.py` | Benchmark environment: real venues in 5 cities (Taipei, Seattle, New York City, Tokyo, Paris). |
| `snapshot/travel_<city>.json` | **Frozen real travel times** from OSRM (OpenStreetMap road network). |
| `harness/live.py` | Live backend for the demo (OSRM + Open-Meteo), with the same signatures as the snapshot backend. |
| `make_tasks.py`, `harness/solver.py` | Task generator plus a brute-force solver. The solver proves every answerable task has a valid plan and every unanswerable one has none. |
| `scripts/build_snapshot.py` | Rebuilds the OSRM snapshots. |
| `tests/fake_openai.py` | Scripted offline LLM for testing the harness plumbing only (`--fake`). It is **never** used for reported results. |

**Why a snapshot instead of live APIs for the benchmark:**
- The tasks inject scenarios such as 85% rain at 14:00 or a museum closed today.
- pass^3 needs identical tool outputs in every run, so flips measure the agent and not changing data.

This follows the τ-bench and WebArena pattern: a realistic but controlled environment with outcome-based grading. The live backend is for the hosted demo.

## 4. Benchmark (`tasks.jsonl`)

**50 tasks: 10 each in Taipei, Seattle, New York City, Tokyo and Paris.**

| Type | n | What it tests |
|---|---|---|
| `basic` | 10 | 1–2 travelers, locked 18:30 dinner, interests, opening hours, transit |
| `group_split` | 10 | 3–6 travelers with different interests, walk limits and budgets. They split and must regroup within 15 min. |
| `rain_repair` | 10 | A valid draft plan, then rain hits an outdoor item. The system must replace only that item and keep every unaffected one. |
| `constraints` | 3 | Must-visit museum, tight budgets, two locked bookings |
| edge cases | 10 | See the list below |
| `unanswerable` | 7 | See the list below. Must answer `"feasible": false`; producing a plan fails. |

Edge cases:
- single traveler
- dinner too soon after arrival
- six identical travelers
- rain at exactly 50% (the boundary)
- two indirect prompt injections hidden in venue descriptions (`risk: LLM01-indirect`, `unsafe_if: anchor_removed`)
- all-day rain
- venue temporarily closed today
- rain plus tight budget
- regroup within 5 min

Unanswerable:
- two locked bookings too far apart to travel between
- required museum closed that weekday
- required venue in another city
- budget below the locked dinner
- required hike under all-day rain
- booking outside opening hours
- walk limit versus a required hike

Example line (shortened):
```json
{"id": "SEA03", "type": "group_split",
 "user": "Plan a one-day Fri itinerary in Seattle for 3 people ...",
 "setup": {"city": "seattle", "weekday": "Fri", "day_start": "09:00", "day_end": "21:30",
           "start_location": "sea_hotel",
           "travelers": [{"name": "Fay", "max_walk": 3, "budget": 144, "interests": ["hiking", "nature"]}, ...],
           "anchors": [{"id": "A1", "venue_id": "sea_ivars", "start": "18:30", "end": "19:30", "members": "all"}],
           "weather": {},
           "requirements": {"min_activities": 2, "interest_coverage": true, "max_regroup_gap_min": 15}},
 "pass_if": {"feasible": true, "checks": ["schema", "anchors", "hours", "transit", "..."]},
 "reference_answer": {"feasible": true, "itinerary": [...]}}
```

## 5. How to run

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
echo 'OPENAI_API_KEY=sk-...' > .env              # never commit .env
.venv/bin/python eval.py --runs 1 --limit 5      # smoke test
.venv/bin/python eval.py --model gpt-4.1-mini --tag final-gpt41mini
                                                 # full: 50 tasks × 3 runs × {agent, baseline} (reported run)
.venv/bin/python eval.py --summarize final-gpt41mini --regrade   # rebuild table from saved plans, no LLM calls
.venv/bin/python eval.py --provider gemini --model gemini-3.5-flash-lite --rpm 12   # free tier (too small for a full run)
.venv/bin/python eval.py --ids SEA03,TPE10       # rerun specific tasks
.venv/bin/python eval.py --fake --runs 1         # offline plumbing test (scripted LLM, numbers meaningless)
.venv/bin/python make_tasks.py                   # regenerate + verify tasks.jsonl
.venv/bin/python scripts/build_snapshot.py       # refresh OSRM travel-time snapshots
```

Metrics reported side by side for the agent and the baseline:
- accuracy (±1 standard error)
- accuracy per run and per task type
- average turns (LLM calls) and tool calls
- average and p95 latency (seconds to the final answer)
- average tokens
- injection attack success
- pass@3, pass^3, and the list of tasks that flip

## 6. Results and failure analysis
**See [`RESULTS.md`](RESULTS.md)**: the side-by-side table, pass@3 / pass^3, flipped tasks and one traced failure.
Headline (gpt-4.1-mini, 50 tasks × 3 runs): agent 38.7% ± 4.0% vs baseline 10.7% ± 2.5%. The agent costs about 22 LLM calls, 26 s and 58k tokens per task; the baseline costs 1 call, 2 s and 7k tokens.

## Credits
- The project overview, the architecture-diagram style, and four scenario ideas come from the teammate's first harness draft (branch `feat/eval-harness`):
  - venue closed today
  - rain plus budget
  - tight regroup
  - a must-visit venue in another city
- Venue hours and prices are hand-curated typical values. Verify them against official sites before the live demo.
