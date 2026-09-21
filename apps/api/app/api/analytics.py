from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attribution, Run, Step
from app.db.session import get_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/failures")
async def failure_distribution(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Attribution.failure_category, func.count()).group_by(Attribution.failure_category)
    )
    return {row[0]: row[1] for row in result.all() if row[0]}


@router.get("/components")
async def component_reliability(session: AsyncSession = Depends(get_session)):
    # Simple heuristic: 1 - (failures attributed / total steps per component)
    total = await session.execute(select(Step.component, func.count()).group_by(Step.component))
    totals = {r[0]: r[1] for r in total.all()}
    attr = await session.execute(
        select(Attribution.responsible_component, func.count()).group_by(Attribution.responsible_component)
    )
    failures = {r[0]: r[1] for r in attr.all()}
    out: dict[str, float] = {}
    for comp, cnt in totals.items():
        fail = failures.get(comp, 0)
        out[comp] = round(max(0.0, 1 - fail / max(1, cnt)), 3)
    # include components with no steps yet as 1.0
    for comp in ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]:
        out.setdefault(comp, 1.0)
    return out


@router.get("/trends")
async def trends(days: int = Query(30, ge=1, le=365), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(func.date(Run.started_at), func.count()).where(Run.status == "failed").group_by(func.date(Run.started_at)).order_by(func.date(Run.started_at))
    )
    series = [{"date": str(r[0]), "failures": r[1]} for r in result.all() if r[0]]
    return {"series": series}
