from fastapi import APIRouter

from app.services import jev_service

router = APIRouter(prefix="/internal/jev", tags=["internal"])


@router.post("/analyze")
async def internal_analyze(payload: dict):
    normalized = payload.get("normalized_trace") or payload.get("state") or payload
    result = await jev_service.analyze_trace(normalized)
    return result
