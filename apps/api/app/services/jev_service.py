"""Jev attribution service — single POST /v1/systemone with parallel Choice/Score/Noul.

Dashboard must never call Jev directly; use POST /internal/jev/analyze which hits this service.
"""
import os
from typing import Any

import httpx

from app.core.config import settings

# Exact enums from spec — do not drift
COMPONENTS = ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]
FAILURE_CATEGORIES = [
    "planning_error",
    "retrieval_error",
    "tool_failure",
    "memory_failure",
    "hallucination",
    "timeout",
    "verification_failure",
]
REPAIR_ACTIONS = [
    "increase_top_k",
    "add_reranker",
    "improve_embeddings",
    "retry_api",
    "enable_citations",
    "human_review",
]

# Heuristic fallback when JEV_API_KEY is not set (local dev / CI mock)
def _mock_analyze(normalized: dict) -> dict[str, Any]:
    steps = normalized.get("steps", []) if isinstance(normalized, dict) else []
    # Simple deterministic mock: weight components by failure status
    weights: dict[str, float] = {c: 0.12 for c in COMPONENTS}
    for s in steps:
        comp = s.get("component")
        if comp in weights and s.get("status") == "failed":
            weights[comp] = 0.91
    # Pick highest weight as responsible
    responsible = max(weights, key=lambda k: weights[k])
    # Failure category heuristic mapping
    cat_map = {
        "retriever": "retrieval_error",
        "planner": "planning_error",
        "tool_router": "tool_failure",
        "memory": "memory_failure",
        "generator": "hallucination",
        "verifier": "verification_failure",
        "external_api": "timeout",
    }
    category = cat_map.get(responsible, "tool_failure")
    failure_step = None
    for idx, s in enumerate(steps, start=1):
        if s.get("status") == "failed":
            failure_step = idx
            break
    return {
        "responsible_component": responsible,
        "component_confidence": float(weights[responsible]),
        "failure_step": failure_step or 1,
        "failure_category": category,
        "category_confidence": 0.87,
        "severity": 0.85,
        "causal_graph": weights,
    }


def _mock_recommend(ctx: dict) -> list[dict]:
    comp = ctx.get("responsible_component")
    mapping = {
        "retriever": [{"action": "add_reranker", "confidence": 0.84}, {"action": "increase_top_k", "confidence": 0.71}],
        "planner": [{"action": "human_review", "confidence": 0.77}],
        "memory": [{"action": "improve_embeddings", "confidence": 0.80}],
        "external_api": [{"action": "retry_api", "confidence": 0.82}],
        "generator": [{"action": "enable_citations", "confidence": 0.79}],
    }
    return mapping.get(comp, [{"action": "human_review", "confidence": 0.65}])


async def analyze_trace(normalized_trace: dict) -> dict[str, Any]:
    """Call Jev /v1/systemone with parallel questions or return mock if no key."""
    api_key = settings.jev_api_key or os.getenv("JEV_API_KEY")
    if not api_key:
        return _mock_analyze(normalized_trace)

    url = f"{settings.jev_base_url.rstrip('/')}{settings.jev_systemone_path}"
    # Jev spec: one state + multiple typed questions in parallel
    payload = {
        "state": normalized_trace,
        "questions": {
            "responsible_component": {"type": "choice", "choices": COMPONENTS},
            "failure_category": {"type": "choice", "choices": FAILURE_CATEGORIES},
            "severity": {"type": "score", "rubric": "Low/Medium/High/Critical"},
            # Noul causal hypotheses — 7 components × failure
            **{f"{c}_caused_failure": {"type": "noul"} for c in COMPONENTS},
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Normalize Jev response to our schema
    # Expected shape varies by Jev version — be defensive
    rc = data.get("responsible_component", {})
    fc = data.get("failure_category", {})
    sev = data.get("severity", {})
    causal = {k: float(v) for k, v in data.items() if k.endswith("_caused_failure")}

    return {
        "responsible_component": rc.get("choice") or rc.get("value") or "retriever",
        "component_confidence": float(rc.get("confidence", 0.8)),
        "failure_step": data.get("failure_step", 1),
        "failure_category": fc.get("choice") or fc.get("value") or "retrieval_error",
        "category_confidence": float(fc.get("confidence", 0.8)),
        "severity": float(sev.get("score", sev.get("value", 0.8)) if isinstance(sev, dict) else sev),
        "causal_graph": causal or {c: 0.1 for c in COMPONENTS},
    }


async def recommend_repair(ctx: dict) -> list[dict]:
    api_key = settings.jev_api_key or os.getenv("JEV_API_KEY")
    if not api_key:
        return _mock_recommend(ctx)

    url = f"{settings.jev_base_url.rstrip('/')}{settings.jev_systemone_path}"
    payload = {
        "state": ctx,
        "questions": {"repair": {"type": "choice", "choices": REPAIR_ACTIONS}},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    choice = data.get("repair", {})
    action = choice.get("choice") or choice.get("value") or "human_review"
    conf = float(choice.get("confidence", 0.7))
    return [{"action": action, "confidence": conf}]
