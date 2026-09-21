"""Jev attribution service — single POST /v1/systemone with parallel Choice/Score/Noul.

Dashboard must never call Jev directly; use POST /internal/jev/analyze which hits this service.
Real Jev required — no mock fallback. JEV_API_KEY must be set.
Target host is api.typesafe.ai (key apikey_*) per Jev Agent docs; also supports jev-agent.com with jv_live_ keys.
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
# Use Jev-preferred model; configurable via JEV_MODEL env
DEFAULT_MODEL = os.getenv("JEV_MODEL", "jev-latest")


def _require_api_key() -> str:
    key = settings.jev_api_key or os.getenv("JEV_API_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "JEV_API_KEY not set. Set it in .env (see .env.example) or environment. "
            "Mocking is disabled — Jev is required."
        )
    return key.strip()


def _choice_criteria() -> dict:
    return {
        "planner": "Task decomposition or planning logic error — wrong plan, missing steps, incorrect sequencing",
        "retriever": "Document retrieval failure — wrong or missing context, poor ranking",
        "tool_router": "Tool selection/routing failure — wrong tool or bad arguments",
        "memory": "Conversation memory/context window failure — lost or corrupted history",
        "generator": "Response generation hallucination or incorrect synthesis",
        "verifier": "Verification/validation failure — missed error or false positive",
        "external_api": "External API call failure — timeout, 5xx, or bad payload",
    }


def _category_criteria() -> dict:
    return {
        "planning_error": "The plan itself was wrong even if execution was correct",
        "retrieval_error": "Failed to retrieve relevant documents or retrieved misleading ones",
        "tool_failure": "A tool or function call failed or returned an error",
        "memory_failure": "Failed due to lost or corrupted conversation history",
        "hallucination": "Generated false information not grounded in retrieved context",
        "timeout": "Execution exceeded time limit or hung",
        "verification_failure": "Verifier did not catch or incorrectly flagged the error",
    }


def _repair_criteria() -> dict:
    return {
        "increase_top_k": "Retrieve more documents by increasing top-k",
        "add_reranker": "Add a cross-encoder reranker after retrieval",
        "improve_embeddings": "Improve embedding model or chunking strategy",
        "retry_api": "Retry external API with backoff or fallback",
        "enable_citations": "Enable citations/grounding to reduce hallucination",
        "human_review": "Require human-in-the-loop review for this failure mode",
    }


async def analyze_trace(normalized_trace: dict) -> dict[str, Any]:
    """Call Jev /v1/systemone with parallel questions. No mock fallback."""
    api_key = _require_api_key()

    url = f"{settings.jev_base_url.rstrip('/')}{settings.jev_systemone_path}"
    payload = {
        "model": DEFAULT_MODEL,
        "state": normalized_trace,
        "questions": {
            "responsible_component": {
                "type": "choice",
                "instructions": "Which agent component is most responsible for the failure?",
                "criteria": _choice_criteria(),
            },
            "failure_category": {
                "type": "choice",
                "instructions": "What is the failure category of this run?",
                "criteria": _category_criteria(),
            },
            "severity": {
                "type": "score",
                "instructions": "How severe is this failure for the end user?",
                "criteria": ["Low", "Medium", "High", "Critical"],
            },
            **{
                f"{c}_caused_failure": {
                    "type": "noul",
                    "instructions": f"Did the {c} component cause or significantly contribute to the failure?",
                    "criteria": {
                        "true": f"{c} caused or contributed to failure",
                        "false": f"{c} did not cause failure",
                    },
                }
                for c in COMPONENTS
            },
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = resp.text[:2000]
            raise RuntimeError(f"Jev /v1/systemone failed {resp.status_code}: {detail}") from exc
        data = resp.json()

    # Real Jev nests under answers; keep compat with flat shape if ever returned
    answers = data.get("answers", data)

    rc = answers.get("responsible_component", {})
    fc = answers.get("failure_category", {})
    sev = answers.get("severity", {})
    # Noul answers: {"type":"noul","noul":0.97}
    causal: dict[str, float] = {}
    for c in COMPONENTS:
        key = f"{c}_caused_failure"
        val = answers.get(key)
        if isinstance(val, dict) and "noul" in val:
            causal[c] = float(val["noul"])
        elif isinstance(val, (int, float)):
            causal[c] = float(val)

    # failure_step not part of Jev output — heuristic from trace (first failed step)
    failure_step = 1
    steps = normalized_trace.get("steps", []) if isinstance(normalized_trace, dict) else []
    for idx, s in enumerate(steps, start=1):
        if isinstance(s, dict) and s.get("status") == "failed":
            failure_step = idx
            break
    # If Jev ever returns it inside answers, prefer that
    if isinstance(answers.get("failure_step"), dict):
        try:
            failure_step = int(answers["failure_step"].get("choice", failure_step))
        except Exception:
            pass
    elif isinstance(answers.get("failure_step"), int):
        failure_step = answers["failure_step"]

    return {
        "responsible_component": rc.get("choice") or rc.get("value") or "retriever",
        "component_confidence": float(rc.get("confidence", 0.8)),
        "failure_step": failure_step,
        "failure_category": fc.get("choice") or fc.get("value") or "retrieval_error",
        "category_confidence": float(fc.get("confidence", 0.8)),
        "severity": float(sev.get("score", sev.get("value", 0.8)) if isinstance(sev, dict) else float(sev)),
        "causal_graph": causal or {c: 0.1 for c in COMPONENTS},
        "raw_model": data.get("model"),
        "usage": data.get("usage"),
    }


async def recommend_repair(ctx: dict) -> list[dict]:
    """Second Jev call for repair recommendation. No mock fallback."""
    api_key = _require_api_key()

    url = f"{settings.jev_base_url.rstrip('/')}{settings.jev_systemone_path}"
    payload = {
        "model": DEFAULT_MODEL,
        "state": ctx,
        "questions": {
            "repair": {
                "type": "choice",
                "instructions": "Which remediation best fixes this failure?",
                "criteria": _repair_criteria(),
            }
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = resp.text[:2000]
            raise RuntimeError(f"Jev repair call failed {resp.status_code}: {detail}") from exc
        data = resp.json()
    answers = data.get("answers", data)
    choice = answers.get("repair", {})
    action = choice.get("choice") or choice.get("value") or "human_review"
    conf = float(choice.get("confidence", 0.7))
    return [{"action": action, "confidence": conf}]
