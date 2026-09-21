"""Smoke: imports and route table — DB not required."""
from apps.api.app.main import app


def test_routes_registered():
    paths = {r.path for r in app.routes}
    assert "/api/v1/runs" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/analytics/failures" in paths
