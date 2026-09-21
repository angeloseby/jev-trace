import asyncio


def test_mock_analyze():
    from apps.api.app.services.jev_service import _mock_analyze  # type: ignore

    r = _mock_analyze({"task": "t", "steps": [{"component": "retriever", "status": "failed"}]})
    assert r["responsible_component"] == "retriever"
    assert r["failure_category"] == "retrieval_error"
    assert r["causal_graph"]["retriever"] == 0.91
