from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ComponentType = Literal[
    "planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"
]


class StepCreate(BaseModel):
    step_number: int
    component: ComponentType
    status: str = "success"
    input: dict = {}
    output: dict = {}
    latency_ms: int | None = None


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
