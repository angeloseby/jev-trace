from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class RunStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class RunCreate(BaseModel):
    task_name: str


class RunComplete(BaseModel):
    status: RunStatus


class RunOut(BaseModel):
    id: UUID
    task_name: str
    status: RunStatus
    started_at: datetime
    ended_at: datetime | None = None
    total_steps: int

    model_config = {"from_attributes": True}
