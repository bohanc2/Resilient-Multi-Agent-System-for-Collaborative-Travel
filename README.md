# Resilient-Multi-Agent-System-for-Collaborative-Travel

Evaluation Harness for Collaborative Multi-Agent Travel Planning (Week 7 Milestone).

## Project Overview
This project benchmarks a collaborative travel planning system coordinating multiple travelers with conflicting preferences, budgets, stamina, and non-negotiable bookings (Hard Anchors). It supports split-and-regroup tracking (arrival time gap $\le$ 15 mins) and contingency handling (rain forecasts, venue closures) via localized replanning.

## Files
- `tasks.jsonl`: 50 benchmark evaluation scenarios:
  - 44 `normal` tasks (diverse cities, 2-5 travelers, budgets, split-and-regroup, hard anchors).
  - 4 `edge_case` tasks (sudden downpour, venue closure, tight 15-min regroup coordination, rain + strict budget).
  - 2 `unanswerable` tasks (physical spatio-temporal impossibility, financial impossibility).
- `generate_tasks.py`: Script to generate or regenerate `tasks.jsonl`.
- `eval.py`: Single standalone automated evaluation script with:
  - Local Mock Environment (`check_venue`, `get_transit_time`, `check_weather`).
  - Deterministic Python Checker (Hard anchors, operating hours, weather contingencies, transit buffers, regroup arrival gap $\le$ 15 mins, budgets, unanswerable rejection).
  - Non-Agentic Baseline (Single LLM turn, no tools, turns = 1).
  - Project Agent MVP (Plan-and-Verify loop, up to 3 turns, localized repair on checker feedback).
  - Parallel execution via `ThreadPoolExecutor`.
  - Side-by-side Markdown comparison table (Accuracy, Average Turns, Average Latency, P95 Latency, Average Tokens).
  - Multi-run Agent robustness report (`pass@3`, `pass^3`, Flaky tasks identification).
  - Full execution traces logged to `eval_logs.json` for Failure Analysis.

## How to Run

### 1. Run Evaluation (Default / Fast Offline Simulation)
```bash
python eval.py
```
Or explicitly specify offline mock mode:
```bash
python eval.py --mock-llm
```

### 2. Run with Live OpenAI API (if OPENAI_API_KEY is configured)
```bash
python eval.py --model gpt-4o-mini --concurrency 8
```

### 3. Regenerate Benchmark Tasks
```bash
python generate_tasks.py
```
