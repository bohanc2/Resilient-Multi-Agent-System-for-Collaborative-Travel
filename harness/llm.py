"""Thin OpenAI wrapper that records one trace span per model call / tool call
(OpenTelemetry GenAI style names: "chat", "execute_tool")."""
from __future__ import annotations

import json
import os
import pathlib
import time


def load_dotenv(path: str = ".env") -> None:
    p = pathlib.Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _clip(x, n=1500):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n} chars]"


class Recorder:
    """Collects spans and usage for one system run on one task."""

    def __init__(self):
        self.spans: list[dict] = []
        self.t0 = time.time()
        self.llm_calls = 0
        self.tool_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def span(self, **kw):
        kw.setdefault("t", round(time.time() - self.t0, 3))
        self.spans.append(kw)

    @property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens


class LLM:
    def __init__(self, model: str, temperature: float | None = 0.0, client=None):
        self.model = model
        self.temperature = temperature
        if client is None:
            from openai import OpenAI
            load_dotenv()
            client = OpenAI(max_retries=6, timeout=120)
        self.client = client

    def chat(self, rec: Recorder, messages: list[dict], node: str, tools=None, json_mode=False):
        kw = dict(model=self.model, messages=messages)
        if self.temperature is not None and not self.model.startswith(("o1", "o3", "o4", "gpt-5")):
            kw["temperature"] = self.temperature
            kw["seed"] = 0
        if tools:
            kw["tools"] = tools
            kw["parallel_tool_calls"] = True
        if json_mode:
            kw["response_format"] = {"type": "json_object"}
        t = time.time()
        err = None
        try:
            resp = self.client.chat.completions.create(**kw)
        except Exception as e:  # recorded in the trace, then re-raised
            err = repr(e)
            rec.span(name="chat", node=node, model=self.model, duration_s=round(time.time() - t, 3), error=err,
                     input=_clip(messages[-1]))
            raise
        msg = resp.choices[0].message
        u = resp.usage
        rec.llm_calls += 1
        rec.input_tokens += u.prompt_tokens
        rec.output_tokens += u.completion_tokens
        out = msg.content or ""
        if msg.tool_calls:
            out = [{"tool": c.function.name, "args": c.function.arguments} for c in msg.tool_calls]
        rec.span(name="chat", node=node, model=self.model, duration_s=round(time.time() - t, 3),
                 input_tokens=u.prompt_tokens, output_tokens=u.completion_tokens,
                 input=_clip(messages[-1]), output=_clip(out, 4000), error=None)
        return msg


def tool_span(rec: Recorder, node: str, name: str, args, fn):
    t = time.time()
    rec.tool_calls += 1
    try:
        out = fn()
        err = None
    except Exception as e:
        out, err = {"error": str(e)}, repr(e)
    rec.span(name="execute_tool", node=node, tool=name, duration_s=round(time.time() - t, 4),
             input=_clip(args), output=_clip(out), error=err)
    return out
