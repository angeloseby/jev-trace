"""Optional Celery bridge — enqueues Jev analysis to worker if Redis/Celery available."""

def enqueue_analyze(run_id: str):
    # Import lazily so API can run without worker deps or Redis
    try:
        from apps.worker.app.celery_app import celery_app
    except Exception:
        # Fallback path when running from apps/api (sys.path includes repo root)
        import sys
        from pathlib import Path

        p = Path(__file__).resolve().parents[2] / "apps" / "worker"
        if str(p.parent) not in sys.path:
            sys.path.insert(0, str(p.parent))
        from app.celery_app import celery_app  # type: ignore

    return celery_app.send_task("app.celery_app.analyze_run", args=[run_id])
