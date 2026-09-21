import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attribution, Failure, Run, Step
from app.db.session import get_session
from app.schemas.attribution import AnalyzeResponse, AttributionOut, GraphOut, GraphEdge, GraphNode
from app.services import jev_service

router = APIRouter(tags=["attributions"])


@router.post("/runs/{run_id}/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    result = await session.execute(select(Step).where(Step.run_id == run_id).order_by(Step.step_number.asc()))
    steps = list(result.scalars().all())

    # Normalize trace for Jev
    normalized = {
        "task": run.task_name,
        "steps": [{"component": s.component, "status": s.status} for s in steps],
    }

    # Prefer async worker if available, with sync fallback (no Redis → still works)
    use_worker = os.getenv("USE_WORKER", "false").lower() == "true"
    jev_result: dict | None = None
    if use_worker:
        try:
            from app.worker_bridge import enqueue_analyze

            task = enqueue_analyze(str(run_id))
            # Return 202 with task id; attribution will be available after worker completes
            # For now return accepted; client can poll GET /attribution
            return AnalyzeResponse(
                run_id=run_id,
                responsible_component={"name": "pending", "confidence": 0.0},
                failure_step={"step_number": 1, "confidence": 0.0},
                failure_category={"name": "pending", "confidence": 0.0},
                severity=0.0,
                causal_graph=None,
            )
        except Exception:
            pass  # fallback to sync
    jev_result = await jev_service.analyze_trace(normalized)

    # Persist attribution
    existing = await session.execute(select(Attribution).where(Attribution.run_id == run_id))
    attr = existing.scalar_one_or_none()
    if attr is None:
        attr = Attribution(
            run_id=run_id,
            responsible_component=jev_result["responsible_component"],
            component_confidence=jev_result["component_confidence"],
            failure_step=jev_result.get("failure_step"),
            failure_category=jev_result["failure_category"],
            category_confidence=jev_result["category_confidence"],
            severity=jev_result["severity"],
            causal_graph=jev_result.get("causal_graph"),
        )
        session.add(attr)
    else:
        attr.responsible_component = jev_result["responsible_component"]
        attr.component_confidence = jev_result["component_confidence"]
        attr.failure_step = jev_result.get("failure_step")
        attr.failure_category = jev_result["failure_category"]
        attr.category_confidence = jev_result["category_confidence"]
        attr.severity = jev_result["severity"]
        attr.causal_graph = jev_result.get("causal_graph")
    # Ensure failures row for analytics parity
    f_res = await session.execute(select(Failure).where(Failure.run_id == run_id))
    if not f_res.scalar_one_or_none():
        session.add(Failure(run_id=run_id, failure_detected=True, reason=jev_result["failure_category"], severity_score=jev_result["severity"]))
    await session.commit()

    return AnalyzeResponse(
        run_id=run_id,
        responsible_component={"name": attr.responsible_component, "confidence": attr.component_confidence},
        failure_step={"step_number": attr.failure_step, "confidence": attr.category_confidence},
        failure_category={"name": attr.failure_category, "confidence": attr.category_confidence},
        severity=attr.severity,
        causal_graph=attr.causal_graph,
    )


@router.get("/runs/{run_id}/attribution", response_model=AttributionOut)
async def get_attribution(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Attribution).where(Attribution.run_id == run_id))
    attr = result.scalar_one_or_none()
    if not attr:
        raise HTTPException(status_code=404, detail="Attribution not found. Run POST /analyze first.")
    return attr


@router.get("/runs/{run_id}/graph", response_model=GraphOut)
async def get_graph(run_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Attribution).where(Attribution.run_id == run_id))
    attr = result.scalar_one_or_none()
    if not attr:
        raise HTTPException(status_code=404, detail="Attribution not found")
    graph = attr.causal_graph or {}
    # Ensure default shape if Jev mock returned flat weights
    nodes = [GraphNode(id=k, weight=float(v)) for k, v in graph.items()] if graph else []
    # Build linear edges following step order for visualization
    edges = []
    for i in range(len(nodes) - 1):
        edges.append(GraphEdge(source=nodes[i].id, target=nodes[i + 1].id))
    return GraphOut(nodes=nodes, edges=edges)
