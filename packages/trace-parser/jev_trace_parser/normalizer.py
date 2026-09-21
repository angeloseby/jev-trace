def normalize_trace(task_name: str, steps: list[dict]) -> dict:
    """Convert raw steps into Jev state: {task, steps:[{component,status}]}."""
    return {
        "task": task_name,
        "steps": [{"component": s.get("component"), "status": s.get("status", "success")} for s in steps],
    }
