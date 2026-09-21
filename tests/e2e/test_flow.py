"""E2E: Run Agent → Collect Trace → Fail → Analyze (Jev) → Dashboard data.

Requires postgres + JEV_API_KEY/TYPESAFE_API_KEY. Worker not required (sync fallback).
"""
import os

import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


async def test_e2e_attribution():
    if not os.getenv("JEV_API_KEY") and not os.getenv("TYPESAFE_API_KEY"):
        from app.core.config import settings

        if not settings.jev_api_key and not getattr(settings, "typesafe_api_key", None):
            pytest.skip("JEV_API_KEY/TYPESAFE_API_KEY not set — e2e requires real Jev")
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create run
        r = await client.post("/api/v1/runs", json={"task_name": "e2e-Find GDP of Brazil"})
        assert r.status_code == 201, r.text
        run_id = r.json()["id"]

        # 2. Collect trace (3 steps, retriever fails)
        await client.post(f"/api/v1/runs/{run_id}/steps", json={"step_number": 1, "component": "planner", "status": "success", "latency_ms": 80})
        await client.post(f"/api/v1/runs/{run_id}/steps", json={"step_number": 2, "component": "retriever", "status": "failed", "latency_ms": 240})
        await client.post(f"/api/v1/runs/{run_id}/steps", json={"step_number": 3, "component": "generator", "status": "failed", "latency_ms": 60})

        # 3. Complete as failed
        await client.post(f"/api/v1/runs/{run_id}/complete", json={"status": "failed"})

        # 4. Analyze via Jev (parallel Choice/Score/Noul)
        a = await client.post(f"/api/v1/runs/{run_id}/analyze")
        assert a.status_code in (200, 202), a.text

        # 5. Poll attribution (sync path returns immediately, worker path needs poll)
        for _ in range(5):
            g = await client.get(f"/api/v1/runs/{run_id}/attribution")
            if g.status_code == 200:
                attr = g.json()
                assert attr["responsible_component"] in ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]
                assert attr["failure_category"] in ["planning_error", "retrieval_error", "tool_failure", "memory_failure", "hallucination", "timeout", "verification_failure"]
                break
        else:
            pytest.fail("Attribution not available after analyze")

        # 6. Graph
        gr = await client.get(f"/api/v1/runs/{run_id}/graph")
        assert gr.status_code == 200, gr.text
        graph = gr.json()
        assert "nodes" in graph and "edges" in graph

        # 7. Recommendations (second Jev call)
        rec = await client.post(f"/api/v1/runs/{run_id}/recommendations")
        assert rec.status_code in (200, 201), rec.text
        assert "recommendations" in rec.json()

        # 8. Analytics
        f = await client.get("/api/v1/analytics/failures")
        assert f.status_code == 200
