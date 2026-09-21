from jev_trace_parser.normalizer import normalize_trace


def test_normalize():
    out = normalize_trace("Find GDP", [{"component": "planner", "status": "success"}, {"component": "retriever", "status": "failed"}])
    assert out == {"task": "Find GDP", "steps": [
        {"component": "planner", "status": "success", "text": "", "latency_ms": None},
        {"component": "retriever", "status": "failed", "text": "", "latency_ms": None},
    ]}


def test_normalize_rich_state():
    out = normalize_trace("t", [{"component": "tool_router", "status": "failed",
                                 "input": {"tool": "calc", "args": "x"},
                                 "output": {"error": "bad arg"}, "latency_ms": 120}])
    step = out["steps"][0]
    assert "calc" in step["text"] and "bad arg" in step["text"]
    assert step["latency_ms"] == 120


def test_normalize_truncates():
    out = normalize_trace("x" * 5000, [{"component": "planner", "input": {"big": "y" * 5000}}])
    assert len(out["task"]) == 1500
    assert len(out["steps"][0]["text"]) <= 600
