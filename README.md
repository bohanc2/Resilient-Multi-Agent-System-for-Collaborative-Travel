# Resilient Multi-Agent System for Collaborative Travel: eval harness

Team: **<Name 1> (<NetID 1>)**, **<Name 2> (<NetID 2>)**

## What is here
| File | Purpose |
|---|---|
| `tasks.jsonl` | 50 tasks in the lecture format (`id`, `type`, `user`, `setup`, `pass_if`). Answerable tasks also carry a solver-verified `reference_answer`. |
| `eval.py` | One script that runs the agent and the baseline on all tasks for N runs, grades them, and writes `results/<tag>/results.{json,md}` and `traces/<tag>/*.json`. |
| `harness/agent.py` | Proposed system: LangGraph supervisor with Base Planner, Group Sync and Contingency sub-agents, a deterministic checker, and ≤3 localized replans. |
| `harness/baseline.py` | Single-Prompt Baseline: one LLM call with no tools and no feedback. It gets all the tool data in the prompt. |
| `harness/checker.py` | Deterministic grader, also used as the agent's checker. It checks locked bookings, opening hours, transit, rain, walk limit, budget, regroup gap, interests, must-visit and preserved draft items. |
| `harness/data.py`, `snapshot/` | Benchmark environment: real Taipei venues and a **frozen OSRM travel-time snapshot**. Weather is injected per scenario. |
| `harness/live.py` | Live backend for the demo (OSRM + Open-Meteo). It has the same signatures as the snapshot backend. |
| `make_tasks.py`, `harness/solver.py` | Regenerate and verify tasks. The brute-force solver proves every answerable task has a valid plan and every unanswerable one has none. |

Why a snapshot: the benchmark needs injected scenarios (85% rain at 14:00, closures) and identical tool outputs across the 3 runs, so pass^3 measures the agent and not changing data. This follows the τ-bench / WebArena pattern of a realistic environment with outcome-based grading.

## Run
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
echo 'OPENAI_API_KEY=sk-...' > .env          # never commit .env
.venv/bin/python eval.py                     # 50 tasks × 3 runs × {agent, baseline}
.venv/bin/python eval.py --runs 1 --limit 5  # smoke test
.venv/bin/python eval.py --fake --runs 1     # offline plumbing test, no API calls
.venv/bin/python make_tasks.py               # regenerate tasks.jsonl
.venv/bin/python scripts/build_snapshot.py   # refresh the OSRM snapshot
```

## Task mix (50)
- basic 10
- group_split 10
- rain_repair 10 (repair a draft plan, keep unaffected items)
- constraints 6
- edge cases 7:
  - single traveler
  - dinner too soon
  - identical preferences
  - rain exactly 50%
  - 2× indirect prompt injection in a venue description (`risk`, `unsafe_if`)
  - all-day rain
- unanswerable 7 (`pass_if: {"reports_infeasible": true}`):
  - impossible locked bookings
  - museum closed that day
  - unknown venue
  - budget below locked dinner
  - required hike under all-day rain
  - booking outside opening hours
  - walk limit vs required hike

## Results and failure analysis
See `results/<tag>/results.md` and `RESULTS.md`.
