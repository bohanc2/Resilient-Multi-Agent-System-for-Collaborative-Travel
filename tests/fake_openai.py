"""Scripted stand-in for the OpenAI client, used only by `eval.py --fake` to test the harness plumbing
offline. It "plans" with the brute-force solver WITHOUT weather knowledge, so rain tasks fail on the first
try and exercise the supervisor / replan path. Its numbers mean nothing about model quality."""
import itertools
import json
from types import SimpleNamespace as NS

from harness.solver import solve

_ids = itertools.count()


def _resp(content=None, tool_calls=None):
    msg = NS(content=content, tool_calls=tool_calls)
    return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=1000, completion_tokens=200))


def _details(messages):
    first_user = next(m for m in messages if m["role"] == "user")["content"]
    if "REQUEST:\n" in first_user:
        first_user = first_user.split("REQUEST:\n", 1)[1]
    return json.loads(first_user)["details"]


def _plan(details):
    p = solve(details)
    return p or {"feasible": False, "reason": "no plan found", "itinerary": []}


class _Completions:
    def create(self, model, messages, tools=None, response_format=None, **kw):
        sys_prompt = messages[0]["content"]
        d = _details(messages)
        if tools is None:  # baseline or supervisor (json mode)
            if "SUPERVISOR" in sys_prompt:
                if "replan budget is used up" in sys_prompt:
                    return _resp(json.dumps({"next": "submit_best", "reason": "fake"}))
                nxt = "contingency" if solve(d) else "declare_infeasible"
                return _resp(json.dumps({"next": nxt, "instruction": "fix it", "reason": "fake"}))
            return _resp(json.dumps(_plan(d)))
        if messages[-1]["role"] == "user":
            return _resp(None, [NS(id=f"c{next(_ids)}", function=NS(name="weather", arguments="{}"))])
        return _resp(None, [NS(id=f"c{next(_ids)}", function=NS(name="propose_plan",
                                                                 arguments=json.dumps({"plan": _plan(d)})))])


class FakeOpenAI:
    def __init__(self):
        self.chat = NS(completions=_Completions())
