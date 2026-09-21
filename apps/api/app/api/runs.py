import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.db.models import Run
from app.db.session import get_session
from app.schemas.common import CursorPage
from app.schemas.run import RunComplete, RunCreate, RunOut

router = APIRouter(prefix="/runs", tags=["runs"])


def _encode_cursor(run: Run) -> str:
    return base64.urlsafe_b64encode(json.dumps({"id": str(run.id), "ts": run.started_at.isoformat() if run.started_at else ""}).encode()).decode()


def _decode_cursor(cursor: str | None) -> tuple[datetime | None, uuid.UUID | None]:
    if not cursor:
        return None, None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        ts = datetime.fromisoformat(data["ts"]) if data.get("ts") else None
        return ts, uuid.UUID(data["id"])
    except Exception:
        return None, None


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_run(request: Request, payload: RunCreate, session: AsyncSession = Depends(get_session)):
    # Use project_id from header X-Project-Id if provided, else default
    from fastapi import Request

    # project handling is optional for backward compat
    run = Run(task_name=payload.task_name, status="running")
    # Try to honor X-Project-Id if caller sets it (dashboard project switcher)
    # We inspect request via dependency injection alternative: use header directly in endpoint would require Request param,
    # so we fallback to default project id if not provided via payload extension
    project_id = getattr(payload, "project_id", None)
    if project_id:
        try:
            import uuid as _uuid

            run.project_id = _uuid.UUID(str(project_id))
        except Exception:
            pass
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
    cur_ts, cur_id = _decode_cursor(cursor)
    # Composite cursor: (started_at, id) for stable pagination
    base = select(Run).order_by(Run.started_at.desc(), Run.id.desc())
    if status_filter:
        base = base.where(Run.status == status_filter)
    if cur_ts and cur_id:
        # tuple comparison for cursor
        base = base.where((Run.started_at < cur_ts) | ((Run.started_at == cur_ts) & (Run.id < cur_id)))
    q = base.limit(limit + 1)
    result = await session.execute(q)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = _encode_cursor(items[-1]) if has_more and items else None
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



