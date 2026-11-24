"""Non-agentic baseline (proposal: Single-Prompt Baseline): one LLM call, no tools, no feedback.
It gets the same rules and ALL the data the tools could return (venues, travel matrix, weather) in the prompt."""
from __future__ import annotations

import json

from .agent import _parse_json
from .llm import LLM, Recorder
from .tools import RULES, TripTools, public_setup


class SinglePromptBaseline:
    def __init__(self, llm: LLM):
        self.llm = llm

    def run(self, task: dict) -> dict:
        rec = Recorder()
        tools = TripTools(task["setup"])
        msgs = [{"role": "system", "content": RULES + "\nAnswer with the plan JSON only."},
                {"role": "user", "content": "DATA (venues, travel minutes, rain probability):\n" + tools.full_dump() +
                 "\n\nREQUEST:\n" + json.dumps({"request": task["user"], "details": public_setup(task["setup"])},
                                                ensure_ascii=False)}]
        error, plan = None, None
        try:
            m = self.llm.chat(rec, msgs, node="baseline", json_mode=True)
            plan = _parse_json(m.content or "")
        except Exception as e:
            error = repr(e)
        return {"plan": plan, "turns": rec.llm_calls, "tool_calls": 0, "input_tokens": rec.input_tokens,
                "output_tokens": rec.output_tokens, "tokens": rec.total_tokens, "replans": 0, "log": [],
                "spans": rec.spans, "error": error}
