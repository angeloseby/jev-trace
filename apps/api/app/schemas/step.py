import difflib
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

ComponentType = Literal[
    "planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"
]

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
VALID = ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]


class StepCreate(BaseModel):
    step_number: int
    component: ComponentType
    status: str = "success"
    input: dict = {}
    output: dict = {}
    latency_ms: int | None = None

    @field_validator("component", mode="before")
    @classmethod
    def _map(cls, v):
        if not isinstance(v, str):
            return v
        low = v.strip().lower()
        if low in VALID:
            return low
        if low in ALIASES:
            return ALIASES[low]
        for k, val in ALIASES.items():
            if k in low:
                return val
        m = difflib.get_close_matches(low, VALID, n=1, cutoff=0.6)
        if m:
            return m[0]
        return v  # let Literal validation emit helpful error with valid list


class StepOut(BaseModel):
    id: UUID
    run_id: UUID
    step_number: int
    component: str
    status: str
    input: dict
    output: dict
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
