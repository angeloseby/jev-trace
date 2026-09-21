import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Run
from app.db.session import get_session
from app.schemas.common import CursorPage
from app.schemas.run import RunComplete, RunCreate, RunOut

router = APIRouter(prefix="/runs", tags=["runs"])


def _encode_cursor(run_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(json.dumps({"id": str(run_id)}).encode()).decode()


def _decode_cursor(cursor: str | None) -> uuid.UUID | None:
    if not cursor:
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return uuid.UUID(data["id"])
    except Exception:
        return None


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(payload: RunCreate, session: AsyncSession = Depends(get_session)):
    run = Run(task_name=payload.task_name, status="running")
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


@router.get("", response_model=CursorPage[RunOut])
async def list_runs(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(Run).order_by(Run.started_at.desc(), Run.id.desc()).limit(limit + 1)
    if status_filter:
        q = q.where(Run.status == status_filter)
    cur_id = _decode_cursor(cursor)
    if cur_id:
        # cursor pagination: fetch after the cursor id
        q = select(Run).where(Run.id < cur_id).order_by(Run.started_at.desc(), Run.id.desc()).limit(limit + 1)
        if status_filter:
            q = q.where(Run.status == status_filter)
    result = await session.execute(q)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = _encode_cursor(items[-1].id) if has_more and items else None
    return CursorPage[RunOut](items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/complete")
async def complete_run(run_id: uuid.UUID, payload: RunComplete, session: AsyncSession = Depends(get_session)):
    from app.db.models import Failure

    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = payload.status.value
    run.ended_at = datetime.now(timezone.utc)
    # Auto-create failure row for analytics & detection parity (Phase 2)
    if payload.status.value == "failed":
        existing = await session.execute(select(Failure).where(Failure.run_id == run_id))
        if not existing.scalar_one_or_none():
            session.add(Failure(run_id=run_id, failure_detected=True, reason="run marked failed", severity_score=0.8))
    elif payload.status.value == "completed":
        existing = await session.execute(select(Failure).where(Failure.run_id == run_id))
        f = existing.scalar_one_or_none()
        if f:
            f.failure_detected = False
    await session.commit()
    return {"success": True, "data": {"id": str(run.id), "status": run.status}}



