"""Shared cursor pagination helpers — replaces duplication in runs.py / steps.py."""

import base64
import json
import uuid
from datetime import datetime


def encode_run_cursor(run) -> str:
    return base64.urlsafe_b64encode(json.dumps({"id": str(run.id), "ts": run.started_at.isoformat() if run.started_at else ""}).encode()).decode()


def decode_run_cursor(cursor: str | None) -> tuple[datetime | None, uuid.UUID | None]:
    if not cursor:
        return None, None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        ts = datetime.fromisoformat(data["ts"]) if data.get("ts") else None
        return ts, uuid.UUID(data["id"])
    except Exception:
        return None, None


def encode_step_cursor(step_number: int, sid: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"n": step_number, "id": sid}).encode()).decode()


def decode_step_cursor(cursor: str | None) -> int | None:
    if not cursor:
        return None
    try:
        return int(json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())["n"])
    except Exception:
        return None
