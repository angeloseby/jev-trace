"""Batch ingestion — Langfuse-compatible POST /api/public/ingestion."""

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.db.models import ApiKey, Project, Run, Step
from app.db.session import get_session

router = APIRouter(tags=["ingest"])


def _parse_basic_public_secret(authorization: str | None, x_api_key: str | None):
    if x_api_key:
        # X-Api-Key: jt_pub_xxx
        return x_api_key, None
    if not authorization:
        return None, None
    # Basic base64(public:secret) or Bearer jt_pub_..._secret
    if authorization.startswith("Basic "):
        import base64

        try:
            decoded = base64.b64decode(authorization[6:]).decode()
            if ":" in decoded:
                pub, sec = decoded.split(":", 1)
                return pub, sec
        except Exception:
            pass
    if authorization.startswith("Bearer "):
        bearer = authorization[7:]
        if ":" in bearer:
            pub, sec = bearer.split(":", 1)
            return pub, sec
        # public key only
        return bearer, None
    return None, None


async def _resolve_project(session: AsyncSession, public_key: str | None, secret: str | None) -> uuid.UUID | None:
    if not public_key:
        # default project for unauthenticated local demo
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    r = await session.execute(select(ApiKey).where(ApiKey.public_key == public_key))
    k = r.scalar_one_or_none()
    if not k:
        return None
    if secret:
        h = hashlib.sha256(secret.encode()).hexdigest()
        if h != k.secret_hash:
            return None
    return k.project_id


@router.post("/public/ingestion")
@router.post("/v1/ingest")
@limiter.limit("60/minute")
async def ingest(
    request: Request,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-Api-Key"),
):
    # Langfuse shape: {"batch": [{"type":"trace-create","body":{"id","name",...}}, {"type":"observation-create", ...}]}
    # JevTrace simplified: same, but we map trace-create → Run, observation-create → Step
    public_key, secret = _parse_basic_public_secret(authorization, x_api_key)
    project_id = await _resolve_project(session, public_key, secret)
    if public_key and not project_id:
        raise HTTPException(status_code=401, detail="Invalid API key")

    batch = payload.get("batch") or payload.get("events") or []
    if isinstance(payload.get("type"), str):
        batch = [payload]

    created_runs = 0
    created_steps = 0
    for evt in batch:
        typ = evt.get("type") or evt.get("eventType") or ""
        body = evt.get("body") or evt
        if typ in ("trace-create", "trace", "run-create"):
            rid = body.get("id")
            try:
                run_id = uuid.UUID(rid) if rid else uuid.uuid4()
            except Exception:
                run_id = uuid.uuid4()
            # idempotent: skip if exists
            existing_run = await session.get(Run, run_id)
            if existing_run:
                continue
            name = body.get("name") or body.get("task_name") or "ingested-trace"
            run = Run(id=run_id, project_id=project_id, task_name=name, status=body.get("status", "running"))
            session.add(run)
            created_runs += 1
        elif typ in ("observation-create", "observation", "span-create", "generation-create", "step-create"):
            tid = body.get("traceId") or body.get("trace_id") or body.get("runId") or body.get("run_id")
            try:
                run_id = uuid.UUID(tid) if tid else None
            except Exception:
                run_id = None
            if not run_id:
                # create default run for orphan observation
                run_id = uuid.uuid4()
                session.add(Run(id=run_id, project_id=project_id, task_name="auto-trace", status="running"))
                created_runs += 1
            # ensure run exists
            existing = await session.get(Run, run_id)
            if not existing:
                session.add(Run(id=run_id, project_id=project_id, task_name="auto-trace", status="running"))
                created_runs += 1
            # next step_number; also ensure run total_steps updated
            # need to fetch run for total_steps increment (handle pending flush)
            run_obj = existing if 'existing' in locals() and existing else await session.get(Run, run_id)
            # if we just created run via session.add without flush, get may return None due to pending; try to find in session
            if not run_obj:
                for obj in session.new:
                    if isinstance(obj, Run) and obj.id == run_id:
                        run_obj = obj
                        break
            r = await session.execute(select(Step).where(Step.run_id == run_id).order_by(Step.step_number.desc()))
            last = r.scalars().first()
            nxt = (last.step_number + 1) if last else 1
            comp = body.get("component") or body.get("name") or "tool_router"
            # reuse validator mapping via direct insert (bypass Pydantic, but normalize)
            from app.schemas.step import ALIASES, VALID

            low = str(comp).lower()
            if low not in VALID:
                low = ALIASES.get(low, low)
                for k, v in ALIASES.items():
                    if k in low:
                        low = v
                        break
                if low not in VALID:
                    low = "tool_router"
            step = Step(
                run_id=run_id,
                step_number=body.get("step_number") or nxt,
                component=low,
                observation_type=body.get("type") or body.get("observationType"),
                model=body.get("model"),
                usage=body.get("usage"),
                input=body.get("input") or body.get("inputs") or {},
                output=body.get("output") or body.get("outputs") or {},
                status=body.get("status", "success"),
                latency_ms=body.get("latency_ms"),
                parent_id=body.get("parentId"),
            )
            session.add(step)
            if run_obj:
                run_obj.total_steps = (run_obj.total_steps or 0) + 1
            created_steps += 1

    await session.commit()
    return {"success": True, "data": {"created_runs": created_runs, "created_steps": created_steps}}
