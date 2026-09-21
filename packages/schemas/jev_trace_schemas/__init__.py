"""Shared schemas — re-exports canonical enums/constants from API spec."""

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
SEVERITY_RUBRIC = ["Low", "Medium", "High", "Critical"]
