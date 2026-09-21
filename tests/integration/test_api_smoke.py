"""Smoke: imports and route table — DB not required."""
from app.main import app


def test_routes_registered():
    # Use openapi to verify routes (handles _IncludedRouter in fastapi 0.1xx)
    openapi = app.openapi()
    paths = set(openapi["paths"].keys())
    assert "/api/v1/runs" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/analytics/failures" in paths
