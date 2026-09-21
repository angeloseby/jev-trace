import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Run, Step
from app.db.session import get_session
from app.schemas.common import CursorPage
from app.schemas.step import StepCreate, StepOut

router = APIRouter(tags=["steps"])


@router.post("/runs/{run_id}/steps", response_model=dict, status_code=201)
async def add_step(run_id: uuid.UUID, payload: StepCreate, session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    step = Step(
        run_id=run_id,
        step_number=payload.step_number,
        component=payload.component,
        status=payload.status,
        input=payload.input,
        output=payload.output,
        latency_ms=payload.latency_ms,
    )
    session.add(step)
    run.total_steps = (run.total_steps or 0) + 1
    await session.commit()
    await session.refresh(step)
    return {"id": str(step.id)}


@router.get("/runs/{run_id}/steps", response_model=CursorPage[StepOut])
async def list_steps(run_id: uuid.UUID, limit: int = 50, cursor: str | None = None, session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    q = select(Step).where(Step.run_id == run_id).order_by(Step.step_number.asc()).limit(limit)
    result = await session.execute(q)
    items = list(result.scalars().all())
    return CursorPage[StepOut](items=items, next_cursor=None, has_more=False)


@router.get("/steps/{step_id}", response_model=StepOut)
async def get_step(step_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    step = await session.get(Step, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return step
