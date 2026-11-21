"""One script: run the agent and the non-agentic baseline on every task, N runs each, grade with the
deterministic checker, and write results.json, results.md (side-by-side table, ±1 SE, per-type accuracy,
pass@3 / pass^3, flipped tasks) and one trace file per run under traces/.

    python eval.py                                  # 50 tasks x 3 runs x {agent, baseline}
    python eval.py --runs 1 --limit 5               # quick smoke test
    python eval.py --ids G03,U01 --systems agent    # rerun a few tasks
    python eval.py --fake                           # offline plumbing test (no API key, scripted LLM)
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import pathlib
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from harness.agent import TravelAgent
from harness.baseline import SinglePromptBaseline
from harness.checker import grade
from harness.llm import LLM


def load_jsonl(path):
    return [json.loads(line) for line in open(path) if line.strip()]


def p95(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(0.95 * len(xs)) - 1)] if xs else 0.0


def se(p, n):
    return math.sqrt(p * (1 - p) / n) if n else 0.0


def build_systems(args):
    client = None
    if args.fake:
        from tests.fake_openai import FakeOpenAI
        client = FakeOpenAI()
    from harness.llm import RateLimiter
    lim = RateLimiter(args.rpm)
    kw = dict(client=client, provider=args.provider, limiter=lim)
    sup = LLM(args.supervisor_model or args.model, **kw)
    wrk = LLM(args.model, **kw)
    base = LLM(args.baseline_model or args.model, **kw)
    return {"agent": TravelAgent(sup, wrk), "baseline": SinglePromptBaseline(base)}


def run_one(system, name, task, run, trace_dir):
    t = time.time()
    out = system.run(task)
    seconds = time.time() - t
    g = grade(out["plan"], task)
    row = {"id": task["id"], "type": task["type"], "system": name, "run": run, "correct": g["passed"],
           "turns": out["turns"], "seconds": round(seconds, 2), "tokens": out["tokens"],
           "tool_calls": out["tool_calls"], "replans": out["replans"], "unsafe": g["unsafe"],
           "violations": g["violations"][:8], "error": out["error"]}
    trace = {"task_id": task["id"], "system": name, "run": run, "user": task["user"], "result": row,
             "final_plan": out["plan"], "graph_log": out["log"], "spans": out["spans"]}
    (trace_dir / f"{name}_r{run}_{task['id']}.json").write_text(json.dumps(trace, ensure_ascii=False, indent=1))
    return row


def summarize(rows, tasks, systems, runs):
    by = defaultdict(list)
    for r in rows:
        by[r["system"]].append(r)
    L = []
    L.append(f"Grading: deterministic checker on the final plan (state check; no LLM judge). "
             f"n = {len(tasks)} tasks × {runs} runs per system; accuracy pooled over runs, ±1 SE = sqrt(p(1-p)/n).\n")
    L.append("| Metric | " + " | ".join(systems) + " |")
    L.append("|---|" + "---|" * len(systems))

    def col(fn):
        return " | ".join(fn(by[s]) for s in systems)

    def acc(rs):
        p = sum(r["correct"] for r in rs) / len(rs)
        return f"{p:.1%} ± {se(p, len(rs)):.1%}"

    L.append("| Task accuracy | " + col(acc) + " |")
    for k in range(1, runs + 1):
        L.append(f"| Accuracy run {k} | " + col(lambda rs: (lambda xs: f"{statistics.mean(xs):.1%} (n={len(xs)})" if xs else "–")([r['correct'] for r in rs if r['run'] == k])) + " |")
    L.append("| Avg turns (LLM calls) | " + col(lambda rs: f"{statistics.mean(r['turns'] for r in rs):.2f}") + " |")
    L.append("| Avg tool calls | " + col(lambda rs: f"{statistics.mean(r['tool_calls'] for r in rs):.2f}") + " |")
    L.append("| Avg latency (s) | " + col(lambda rs: f"{statistics.mean(r['seconds'] for r in rs):.1f}") + " |")
    L.append("| p95 latency (s) | " + col(lambda rs: f"{p95([r['seconds'] for r in rs]):.1f}") + " |")
    L.append("| Avg tokens | " + col(lambda rs: f"{statistics.mean(r['tokens'] for r in rs):,.0f}") + " |")
    inj = [t["id"] for t in tasks if t.get("unsafe_if")]
    if inj:
        L.append("| Injection attack success (unsafe) | " + col(
            lambda rs: f"{sum(r['unsafe'] for r in rs if r['id'] in inj)}/{sum(1 for r in rs if r['id'] in inj)}") + " |")
    passk = {}
    for s in systems:
        per = defaultdict(list)
        for r in by[s]:
            per[r["id"]].append(r["correct"])
        n = len(per)
        passk[s] = dict(per=per, at=sum(any(v) for v in per.values()) / n, hat=sum(all(v) for v in per.values()) / n,
                        flips=sorted(i for i, v in per.items() if len(set(v)) > 1))
    L.append(f"| pass@{runs} (≥1 of {runs} passes) | " + " | ".join(f"{passk[s]['at']:.1%}" for s in systems) + " |")
    L.append(f"| pass^{runs} (all {runs} pass) | " + " | ".join(f"{passk[s]['hat']:.1%}" for s in systems) + " |")
    L.append(f"| Tasks that flip | " + " | ".join(str(len(passk[s]['flips'])) for s in systems) + " |")

    L.append("\n### Accuracy by task type\n")
    types = list(dict.fromkeys(t["type"] for t in tasks))
    L.append("| Type | n | " + " | ".join(systems) + " |")
    L.append("|---|---|" + "---|" * len(systems))
    for ty in types:
        n = sum(1 for t in tasks if t["type"] == ty)
        L.append(f"| {ty} | {n} | " + " | ".join(
            f"{statistics.mean(r['correct'] for r in by[s] if r['type'] == ty):.0%}" for s in systems) + " |")

    L.append(f"\n### Tasks whose outcome flips across the {runs} runs\n")
    for s in systems:
        fl = passk[s]["flips"]
        desc = ", ".join(f"{i} ({''.join('P' if x else 'F' for x in passk[s]['per'][i])})" for i in fl) or "none"
        L.append(f"- **{s}**: {desc}")
    L.append(f"\n### Tasks failed in every run\n")
    for s in systems:
        bad = sorted(i for i, v in passk[s]["per"].items() if not any(v))
        L.append(f"- **{s}**: {', '.join(bad) or 'none'}")
    return "\n".join(L), passk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks.jsonl")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--systems", default="agent,baseline")
    ap.add_argument("--model", default="gpt-4.1-mini", help="worker model (and default for the others)")
    ap.add_argument("--supervisor-model", default=None)
    ap.add_argument("--baseline-model", default=None)
    ap.add_argument("--provider", default="openai", choices=["openai", "gemini", "groq"],
                    help="OpenAI-compatible endpoint; gemini/groq have free tiers")
    ap.add_argument("--rpm", type=float, default=None, help="global requests-per-minute cap (free tiers)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--tag", default=None, help="output folder name under results/ and traces/")
    ap.add_argument("--summarize", default=None, metavar="TAG", help="only rebuild the table from results/TAG/rows.jsonl")
    ap.add_argument("--regrade", action="store_true", help="with --summarize: re-grade saved plans from traces")
    ap.add_argument("--fake", action="store_true", help="scripted offline LLM, for testing the harness only")
    args = ap.parse_args()

    tasks = load_jsonl(args.tasks)
    if args.summarize:  # rebuild the table from a (possibly partial) rows.jsonl
        d = pathlib.Path("results") / args.summarize
        rows = load_jsonl(d / "rows.jsonl") if (d / "rows.jsonl").exists() else json.loads((d / "results.json").read_text())
        done = {r["id"] for r in rows}
        tasks = [t for t in tasks if t["id"] in done]
        runs = max(r["run"] for r in rows)
        names = list(dict.fromkeys(r["system"] for r in sorted(rows, key=lambda r: r["system"])))
        if args.regrade:  # re-grade the saved final plans with the current checker (no LLM calls)
            by_id = {t["id"]: t for t in tasks}
            for r in rows:
                tr = json.loads((pathlib.Path("traces") / args.summarize / f"{r['system']}_r{r['run']}_{r['id']}.json").read_text())
                g = grade(tr["final_plan"], by_id[r["id"]])
                r.update(correct=g["passed"], unsafe=g["unsafe"], violations=g["violations"][:8])
            (d / "results.json").write_text(json.dumps(sorted(rows, key=lambda r: (r["system"], r["run"], r["id"])),
                                                       ensure_ascii=False, indent=1))
        table, _ = summarize(rows, tasks, names, runs)
        if args.regrade:
            md = (d / "results.md").read_text()
            head = md.split("Grading:")[0]
            (d / "results.md").write_text(head + table + "\n")
        print(table)
        return
    if args.ids:
        keep = set(args.ids.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    if args.limit:
        tasks = tasks[:args.limit]
    names = args.systems.split(",")
    systems = build_systems(args)
    tag = args.tag or datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ("-fake" if args.fake else "")
    res_dir, trace_dir = pathlib.Path("results") / tag, pathlib.Path("traces") / tag
    res_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(n, t, k) for k in range(1, args.runs + 1) for n in names for t in tasks]
    rows = []
    t0 = time.time()
    with ThreadPoolExecutor(args.concurrency) as ex:
        futs = {ex.submit(run_one, systems[n], n, t, k, trace_dir): (n, t["id"], k) for n, t, k in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            n, tid, k = futs[f]
            try:
                r = f.result()
            except Exception as e:  # harness bug guard: never lose the whole run
                r = {"id": tid, "type": next(t["type"] for t in tasks if t["id"] == tid), "system": n, "run": k,
                     "correct": False, "turns": 0, "seconds": 0, "tokens": 0, "tool_calls": 0, "replans": 0,
                     "unsafe": False, "violations": [], "error": repr(e)}
            rows.append(r)
            with open(res_dir / "rows.jsonl", "a") as fh:  # incremental, survives an interrupted run
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"[{i}/{len(jobs)}] {n:8s} run{k} {tid}: {'PASS' if r['correct'] else 'fail'} "
                  f"turns={r['turns']} {r['seconds']}s tok={r['tokens']}"
                  + (f" ERR {r['error'][:80]}" if r.get("error") else ""), flush=True)
    rows.sort(key=lambda r: (r["system"], r["run"], r["id"]))
    (res_dir / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    table, passk = summarize(rows, tasks, names, args.runs)
    header = (f"# Results ({tag})\n\nProvider: {args.provider}. Models: worker={args.model}, supervisor={args.supervisor_model or args.model}, "
              f"baseline={args.baseline_model or args.model}; temperature 0; wall time {time.time() - t0:.0f}s; "
              f"concurrency {args.concurrency}.\n\n")
    (res_dir / "results.md").write_text(header + table + "\n")
    print("\n" + header + table)
    print(f"\nwrote {res_dir}/results.json, {res_dir}/results.md, traces in {trace_dir}/")


if __name__ == "__main__":
    main()
