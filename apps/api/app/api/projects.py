import secrets
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiKey, Project
from app.db.session import get_session
from app.schemas.project import ApiKeyCreate, ApiKeyOut, ApiKeyWithSecret, ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Project).order_by(Project.created_at))
    return list(r.scalars().all())


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(payload: ProjectCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(Project).where(Project.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Project name exists")
    p = Project(name=payload.name)
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    p = await session.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.get("/{project_id}/api-keys", response_model=list[ApiKeyOut])
async def list_keys(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    p = await session.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    r = await session.execute(select(ApiKey).where(ApiKey.project_id == project_id))
    return list(r.scalars().all())


@router.post("/{project_id}/api-keys", response_model=ApiKeyWithSecret, status_code=201)
async def create_key(project_id: uuid.UUID, payload: ApiKeyCreate, session: AsyncSession = Depends(get_session)):
    p = await session.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    public_key = f"jt_pub_{secrets.token_hex(12)}"
    secret_raw = f"jt_sec_{secrets.token_hex(24)}"
    secret_hash = hashlib.sha256(secret_raw.encode()).hexdigest()
    k = ApiKey(project_id=project_id, public_key=public_key, secret_hash=secret_hash, name=payload.name)
    session.add(k)
    await session.commit()
    await session.refresh(k)
    return ApiKeyWithSecret(id=k.id, project_id=k.project_id, public_key=k.public_key, name=k.name, created_at=k.created_at, secret_key=secret_raw)


@router.delete("/{project_id}/api-keys/{key_id}", status_code=204)
async def delete_key(project_id: uuid.UUID, key_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    k = await session.get(ApiKey, key_id)
    if not k or k.project_id != project_id:
        raise HTTPException(status_code=404, detail="Key not found")
    await session.delete(k)
    await session.commit()
