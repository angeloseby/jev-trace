"""Convert raw steps into Jev state.

Rich state (v2): {task, steps:[{component, status, text, latency_ms}]}.
`text` carries truncated input/output so Jev can see tool mechanics —
component+status alone caused hallucination bias on Who&When Pro
(see docs/benchmark-results.md). Accepts dicts or ORM-like objects.
"""

import json

TASK_CHARS = 1500
STEP_CHARS = 600


def _get(s, key, default=None):
    if isinstance(s, dict):
        return s.get(key, default)
    return getattr(s, key, default)


def _text_of(s):
    parts = []
    for key in ("input", "output"):
        v = _get(s, key)
        if v:
            try:
                parts.append(json.dumps(v, default=str)[:STEP_CHARS])
            except Exception:
                parts.append(str(v)[:STEP_CHARS])
    t = _get(s, "text")
    if t:
        parts.append(str(t)[:STEP_CHARS])
    return " ".join(parts)[:STEP_CHARS]


def normalize_trace(task_name: str, steps: list) -> dict:
    """Normalize task + steps into Jev input state."""
    return {
        "task": str(task_name or "")[:TASK_CHARS],
        "steps": [
            {
                "component": _get(s, "component"),
                "status": _get(s, "status", "success"),
                "text": _text_of(s),
                "latency_ms": _get(s, "latency_ms"),
            }
            for s in steps
        ],
    }
