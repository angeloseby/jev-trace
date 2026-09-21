import os

import pytest

pytestmark = pytest.mark.asyncio


async def test_jev_live_analyze():
    """Requires real JEV_API_KEY/TYPESAFE_API_KEY — no mocking, via SDK."""
    if not os.getenv("JEV_API_KEY") and not os.getenv("TYPESAFE_API_KEY"):
        from app.core.config import settings

        if not settings.jev_api_key and not getattr(settings, "typesafe_api_key", None):
            pytest.skip("JEV_API_KEY/TYPESAFE_API_KEY not set — real Jev required via SDK")
    from app.services.jev_service import analyze_trace

    result = await analyze_trace(
        {"task": "Find GDP of Brazil", "steps": [{"component": "retriever", "status": "failed"}]}
    )
    assert "responsible_component" in result
    assert "failure_category" in result
    assert "severity" in result
    assert "causal_graph" in result
    assert result["responsible_component"] in [
        "planner",
        "retriever",
        "tool_router",
        "memory",
        "generator",
        "verifier",
        "external_api",
    ]
