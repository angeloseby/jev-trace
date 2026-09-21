"""Shared schemas — single source for enums/constants and component aliases."""

COMPONENTS = ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]

# Canonical aliases for forgiving ingestion (llm -> generator, etc.)
ALIASES = {
    "llm": "generator",
    "chat_model": "generator",
    "chat": "generator",
    "model": "generator",
    "search": "retriever",
    "query": "retriever",
    "retrieval": "retriever",
    "embedding": "retriever",
    "tool": "tool_router",
    "agent": "planner",
    "chain": "planner",
    "validator": "verifier",
    "validation": "verifier",
    "api": "external_api",
    "external": "external_api",
}
VALID_COMPONENTS = COMPONENTS
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
