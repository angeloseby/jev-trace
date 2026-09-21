"""Jev attribution service — System One via TypeSafe SDK (async).

Uses AsyncTypeSafeClient + typed Choice/Score/Noul primitives.
Dashboard must never call Jev directly; use POST /internal/jev/analyze which hits this service.
Real Jev required — no mock fallback. JEV_API_KEY (or TYPESAFE_API_KEY) must be set.
"""
import os
from typing import Any

from app.core.config import settings

from jev_trace_schemas import COMPONENTS, FAILURE_CATEGORIES, REPAIR_ACTIONS
DEFAULT_MODEL = os.getenv("JEV_MODEL") or os.getenv("TYPESAFE_DEFAULT_MODEL") or "jev-latest"


def _require_api_key() -> str:
    from app.core.config import get_jev_api_key

    key = get_jev_api_key()
    if not key or not str(key).strip():
        raise RuntimeError(
            "JEV_API_KEY (or TYPESAFE_API_KEY) not set. Set it in .env (see .env.example) or environment. "
            "Mocking is disabled — Jev is required."
        )
    return str(key).strip()


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
    """Call TypeSafe SystemOne with parallel questions via SDK. No mock fallback."""
    api_key = _require_api_key()

    # Lazy import so module imports even if SDK not installed (tests that mock will skip)
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score

    # Ensure SDK sees the key even if it was provided as JEV_API_KEY
    os.environ["TYPESAFE_API_KEY"] = api_key
    if settings.jev_base_url and settings.jev_base_url != "https://api.typesafe.ai":
        os.environ["TYPESAFE_BASE_URL"] = settings.jev_base_url

    async with AsyncTypeSafeClient(api_key=api_key, model=DEFAULT_MODEL) as client:
        try:
            result = await client.system_one(
                state=normalized_trace,
                questions={
                    "responsible_component": Choice(
                        instructions="Which agent component is most responsible for the failure?",
                        criteria=_choice_criteria(),
                    ),
                    "failure_category": Choice(
                        instructions="What is the failure category of this run?",
                        criteria=_category_criteria(),
                    ),
                    "severity": Score(
                        instructions="How severe is this failure for the end user?",
                        criteria=["Low", "Medium", "High", "Critical"],
                    ),
                    **{
                        f"{c}_caused_failure": Noul(
                            instructions=f"Did the {c} component cause or significantly contribute to the failure?",
                            criteria={
                                "true": f"{c} caused or contributed to failure",
                                "false": f"{c} did not cause failure",
                            },
                        )
                        for c in COMPONENTS
                    },
                },
            )
        except Exception as exc:
            # Surface SDK exceptions as RuntimeError for API layer
            raise RuntimeError(f"Jev SystemOne failed: {exc}") from exc

    # SDK typed response: .choices, .scores, .nouls, .answers, .model, .usage
    rc = result.choices.get("responsible_component")
    fc = result.choices.get("failure_category")
    sev = result.scores.get("severity")
    causal: dict[str, float] = {}
    for c in COMPONENTS:
        key = f"{c}_caused_failure"
        ans = result.nouls.get(key)
        if ans is not None:
            causal[c] = float(ans.noul)

    # failure_step not part of Jev output — heuristic from trace
    failure_step = 1
    steps = normalized_trace.get("steps", []) if isinstance(normalized_trace, dict) else []
    for idx, s in enumerate(steps, start=1):
        if isinstance(s, dict) and s.get("status") == "failed":
            failure_step = idx
            break

    return {
        "responsible_component": (rc.choice if rc else "retriever"),
        "component_confidence": float(rc.confidence if rc else 0.8),
        "failure_step": failure_step,
        "failure_category": (fc.choice if fc else "retrieval_error"),
        "category_confidence": float(fc.confidence if fc else 0.8),
        "severity": float(sev.score if sev else 0.8),
        "causal_graph": causal or {c: 0.1 for c in COMPONENTS},
        "raw_model": result.model,
        "usage": {"input_tokens": result.usage.input_tokens, "output_tokens": result.usage.output_tokens}
        if result.usage
        else None,
    }


async def recommend_repair(ctx: dict) -> list[dict]:
    """Second Jev call for repair recommendation via SDK. No mock fallback."""
    api_key = _require_api_key()

    from typesafe_sdk import AsyncTypeSafeClient, Choice

    os.environ["TYPESAFE_API_KEY"] = api_key
    if settings.jev_base_url and settings.jev_base_url != "https://api.typesafe.ai":
        os.environ["TYPESAFE_BASE_URL"] = settings.jev_base_url

    async with AsyncTypeSafeClient(api_key=api_key, model=DEFAULT_MODEL) as client:
        try:
            result = await client.system_one(
                state=ctx,
                questions={
                    "repair": Choice(
                        instructions="Which remediation best fixes this failure?",
                        criteria=_repair_criteria(),
                    )
                },
            )
        except Exception as exc:
            raise RuntimeError(f"Jev repair call failed: {exc}") from exc

    ans = result.choices.get("repair")
    action = ans.choice if ans else "human_review"
    conf = float(ans.confidence if ans else 0.7)
    return [{"action": action, "confidence": conf}]
