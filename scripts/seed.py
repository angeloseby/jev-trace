"""Seed demo data via API (requires API running at :8000)."""

import asyncio
import os
import sys

API = os.getenv("API_BASE", "http://localhost:8000")

DEMO_TRACES = [
    {
        "task_name": "Find GDP of Brazil",
        "steps": [
            {"step_number": 1, "component": "planner", "status": "success", "input": {"goal": "GDP Brazil"}, "output": {"plan": "retrieve then generate"}, "latency_ms": 120},
            {"step_number": 2, "component": "retriever", "status": "failed", "input": {"query": "Brazil GDP 2024"}, "output": {"documents": 0, "error": "no results"}, "latency_ms": 280},
            {"step_number": 3, "component": "generator", "status": "failed", "input": {"prompt": "summarize"}, "output": {"text": "unknown"}, "latency_ms": 80},
        ],
    },
    {
        "task_name": "Tool-routed QA",
        "steps": [
            {"step_number": 1, "component": "planner", "status": "success", "latency_ms": 90},
            {"step_number": 2, "component": "tool_router", "status": "failed", "input": {"tool": "calculator"}, "output": {"error": "tool not found"}, "latency_ms": 45},
            {"step_number": 3, "component": "generator", "status": "failed", "latency_ms": 60},
        ],
    },
    {
        "task_name": "Memory QA",
        "steps": [
            {"step_number": 1, "component": "memory", "status": "failed", "input": {"history": 5}, "output": {"truncated": True}, "latency_ms": 30},
            {"step_number": 2, "component": "generator", "status": "failed", "latency_ms": 70},
        ],
    },
]

try:
    import httpx
except ImportError:
    print("httpx not installed — pip install httpx")
    sys.exit(1)


async def seed_one(trace: dict):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API}/api/v1/runs", json={"task_name": trace["task_name"]})
        r.raise_for_status()
        run_id = r.json()["id"]
        print(f"Created run {run_id} ({trace['task_name']})")
        for s in trace["steps"]:
            await client.post(f"{API}/api/v1/runs/{run_id}/steps", json=s)
        await client.post(f"{API}/api/v1/runs/{run_id}/complete", json={"status": "failed"})
        # Trigger Jev attribution (requires JEV_API_KEY)
        try:
            a = await client.post(f"{API}/api/v1/runs/{run_id}/analyze")
            print(f"  analyze {a.status_code}: {a.text[:300]}")
            # Also trigger recommendations
            rec = await client.post(f"{API}/api/v1/runs/{run_id}/recommendations")
            print(f"  recommendations {rec.status_code}: {rec.text[:300]}")
        except Exception as e:
            print(f"  analyze failed (no JEV_API_KEY?): {e}")
        return run_id


async def main():
    print(f"Seeding to {API} …")
    for t in DEMO_TRACES:
        await seed_one(t)
    print("Done. Check dashboard at http://localhost:3000/runs and analytics.")


if __name__ == "__main__":
    asyncio.run(main())
