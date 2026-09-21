from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str


class ProjectOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str | None = None


class ApiKeyOut(BaseModel):
    id: UUID
    project_id: UUID
    public_key: str
    name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyWithSecret(ApiKeyOut):
    secret_key: str  # only returned once on creation
