from jev_trace_parser.normalizer import normalize_trace


def test_normalize():
    out = normalize_trace("Find GDP", [{"component": "planner", "status": "success"}, {"component": "retriever", "status": "failed"}])
    assert out == {"task": "Find GDP", "steps": [{"component": "planner", "status": "success"}, {"component": "retriever", "status": "failed"}]}
