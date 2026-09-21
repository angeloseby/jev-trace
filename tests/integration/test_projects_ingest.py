"""Projects + Ingest + Component alias integration."""
import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


async def test_projects_and_keys():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # create project
        r = await c.post("/api/v1/projects", json={"name": "proj-test-alias"})
        # may be 201 or 409 if exists from previous run
        assert r.status_code in (201, 409), r.text
        if r.status_code == 409:
            # fetch existing
            r2 = await c.get("/api/v1/projects")
            proj = next(p for p in r2.json() if p["name"] == "proj-test-alias")
            pid = proj["id"]
        else:
            pid = r.json()["id"]
        # create key
        k = await c.post(f"/api/v1/projects/{pid}/api-keys", json={"name": "test-key"})
        assert k.status_code == 201, k.text
        data = k.json()
        assert data["public_key"].startswith("jt_pub_")
        assert "secret_key" in data
        # list keys
        lk = await c.get(f"/api/v1/projects/{pid}/api-keys")
        assert lk.status_code == 200
        assert len(lk.json()) >= 1


async def test_component_alias_and_ingest_batch():
    from app.main import app
    import base64

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # create project+key for batch auth
        r = await c.post("/api/v1/projects", json={"name": "proj-batch"})
        if r.status_code == 409:
            r2 = await c.get("/api/v1/projects")
            pid = next(p for p in r2.json() if p["name"] == "proj-batch")["id"]
        else:
            pid = r.json()["id"]
        k = await c.post(f"/api/v1/projects/{pid}/api-keys", json={"name": "batch-key"})
        pub = k.json()["public_key"]
        sec = k.json()["secret_key"]
        tok = base64.b64encode(f"{pub}:{sec}".encode()).decode()
        # alias via normal steps endpoint: llm -> generator
        run = await c.post("/api/v1/runs", json={"task_name": "alias-test"})
        rid = run.json()["id"]
        s = await c.post(f"/api/v1/runs/{rid}/steps", json={"step_number": 1, "component": "llm", "status": "success"})
        assert s.status_code == 201, s.text
        # verify stored as generator via GET
        steps = await c.get(f"/api/v1/runs/{rid}/steps")
        assert steps.json()["items"][0]["component"] == "generator"
        # batch ingest with llm alias via public ingestion
        import uuid

        tid = str(uuid.uuid4())
        batch = [{"type": "trace-create", "body": {"id": tid, "name": "batch-alias"}}, {"type": "observation-create", "body": {"traceId": tid, "component": "search", "input": {"q": "hi"}}}]
        br = await c.post("/api/public/ingestion", json={"batch": batch}, headers={"Authorization": f"Basic {tok}"})
        assert br.status_code == 200, br.text
        assert br.json()["data"]["created_steps"] == 1
        # verify search -> retriever
        sr = await c.get(f"/api/v1/runs/{tid}/steps")
        assert sr.json()["items"][0]["component"] == "retriever"


async def test_rate_limit_envelope():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # invalid component should give 422 envelope with valid_components
        run = await c.post("/api/v1/runs", json={"task_name": "envelope-test"})
        rid = run.json()["id"]
        bad = await c.post(f"/api/v1/runs/{rid}/steps", json={"step_number": 1, "component": "unknown_xyz_invalid", "status": "success"})
        assert bad.status_code == 422, bad.text
        body = bad.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "valid_components" in body["error"]["details"]
