import os

from celery import Celery

broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery("jevtrace", broker=broker, backend=backend)
celery_app.conf.task_routes = {"app.tasks.*": {"queue": "default"}}
celery_app.conf.update(task_track_started=True, task_acks_late=True)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def analyze_run(self, run_id: str):
    """Celery task: load trace from DB, call Jev via SDK, persist attribution."""
    import asyncio

    from sqlalchemy import select

    # Re-use API's models/session/jev_service (worker shares packages volume)
    # Add apps/api to path if not already
    import sys
    from pathlib import Path

    api_path = Path(__file__).resolve().parents[2] / "apps" / "api"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    from app.db.session import async_session
    from app.db.models import Attribution, Run, Step
    from app.services import jev_service

    async def _run():
        async with async_session() as session:
            run = await session.get(Run, __import__("uuid").UUID(run_id))
            if not run:
                return {"run_id": run_id, "error": "Run not found"}
            result = await session.execute(select(Step).where(Step.run_id == run.id).order_by(Step.step_number.asc()))
            steps = list(result.scalars().all())
            normalized = {"task": run.task_name, "steps": [{"component": s.component, "status": s.status} for s in steps]}
            jev_result = await jev_service.analyze_trace(normalized)
            existing = await session.execute(select(Attribution).where(Attribution.run_id == run.id))
            attr = existing.scalar_one_or_none()
            if attr is None:
                attr = Attribution(
                    run_id=run.id,
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
            # Also auto-create failure row for analytics parity
            from app.db.models import Failure

            f_existing = await session.execute(select(Failure).where(Failure.run_id == run.id))
            if not f_existing.scalar_one_or_none():
                session.add(Failure(run_id=run.id, failure_detected=True, reason=jev_result["failure_category"], severity_score=jev_result["severity"]))
            await session.commit()
            return {"run_id": run_id, "responsible_component": jev_result["responsible_component"]}

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        # Retry on transient Jev/DB errors
        raise self.retry(exc=exc) from exc
