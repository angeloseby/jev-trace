"""API → DB integration (requires postgres at localhost:5432, populated by alembic)."""
import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


async def test_create_run_and_steps():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create run
        r = await client.post("/api/v1/runs", json={"task_name": "integration-test"})
        assert r.status_code == 201, r.text
        run_id = r.json()["id"]

        # Add steps
        s = await client.post(f"/api/v1/runs/{run_id}/steps", json={"step_number": 1, "component": "planner", "status": "success", "input": {}, "output": {}, "latency_ms": 10})
        assert s.status_code == 201, s.text
        s = await client.post(f"/api/v1/runs/{run_id}/steps", json={"step_number": 2, "component": "retriever", "status": "failed", "input": {"q": "x"}, "output": {}, "latency_ms": 50})
        assert s.status_code == 201, s.text

        # List steps (cursor pagination)
        ls = await client.get(f"/api/v1/runs/{run_id}/steps?limit=10")
        assert ls.status_code == 200, ls.text
        data = ls.json()
        assert len(data["items"]) == 2

        # Complete as failed (should auto-create Failure)
        c = await client.post(f"/api/v1/runs/{run_id}/complete", json={"status": "failed"})
        assert c.status_code == 200, c.text

        # Get run
        g = await client.get(f"/api/v1/runs/{run_id}")
        assert g.status_code == 200
        assert g.json()["status"] == "failed"

        # Analytics should include this run after attribution (at least structure)
        a = await client.get("/api/v1/analytics/trends")
        assert a.status_code == 200


async def test_pagination_runs():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ensure at least 2 runs exist
        for i in range(2):
            await client.post("/api/v1/runs", json={"task_name": f"page-{i}"})
        r1 = await client.get("/api/v1/runs?limit=1")
        assert r1.status_code == 200
        data = r1.json()
        assert "items" in data and "has_more" in data
        if data["has_more"]:
            assert data["next_cursor"] is not None
