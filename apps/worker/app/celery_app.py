import os

from celery import Celery

broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery("jevtrace", broker=broker, backend=backend)
celery_app.conf.task_routes = {"app.tasks.*": {"queue": "default"}}


@celery_app.task
def analyze_run(run_id: str):
    # Placeholder — Phase 4 will enqueue Jev analysis here and write attributions
    return {"run_id": run_id, "status": "queued"}
