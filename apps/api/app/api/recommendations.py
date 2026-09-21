import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attribution, Recommendation
from app.db.session import get_session
from app.schemas.recommendation import RecommendationListOut, RecommendationOut
from app.services import jev_service

router = APIRouter(tags=["recommendations"])


@router.post("/runs/{run_id}/recommendations", response_model=RecommendationListOut, status_code=201)
async def generate_recommendations(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    attr_result = await session.execute(select(Attribution).where(Attribution.run_id == run_id))
    attr = attr_result.scalar_one_or_none()
    if not attr:
        raise HTTPException(status_code=404, detail="Attribution not found. Run POST /analyze first.")

    jev_recs = await jev_service.recommend_repair(
        {"responsible_component": attr.responsible_component, "failure_category": attr.failure_category}
    )

    # Persist (replace existing)
    existing = await session.execute(select(Recommendation).where(Recommendation.run_id == run_id))
    for r in existing.scalars().all():
        await session.delete(r)

    recs = []
    for rec in jev_recs:
        obj = Recommendation(run_id=run_id, recommendation=rec["action"], confidence=rec["confidence"])
        session.add(obj)
        recs.append(obj)
    await session.commit()

    return RecommendationListOut(
        recommendations=[RecommendationOut(recommendation=r.recommendation, confidence=r.confidence) for r in recs]
    )


@router.get("/runs/{run_id}/recommendations", response_model=RecommendationListOut)
async def get_recommendations(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Recommendation).where(Recommendation.run_id == run_id))
    rows = list(result.scalars().all())
    return RecommendationListOut(
        recommendations=[RecommendationOut(recommendation=r.recommendation, confidence=r.confidence) for r in rows]
    )
