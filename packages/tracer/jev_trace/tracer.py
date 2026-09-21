"""Core tracer — auto-creates runs/steps with background POST."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager, asynccontextmanager
from typing import Any

import httpx

try:
    # Single source when installed in monorepo; fallback keeps PyPI package standalone
    from jev_trace_schemas import ALIASES as _ALIASES
    from jev_trace_schemas import COMPONENTS
except Exception:
    COMPONENTS = ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]

    _ALIASES = {
        "llm": "generator",
        "chat_model": "generator",
        "chat": "generator",
        "model": "generator",
        "search": "retriever",
        "query": "retriever",
        "retrieval": "retriever",
        "embedding": "retriever",
        "tool": "tool_router",
        "agent": "planner",
        "chain": "planner",
        "validator": "verifier",
        "validation": "verifier",
        "api": "external_api",
        "external": "external_api",
    }


def normalize_component(raw: str) -> str:
    low = (raw or "").strip().lower()
    if not low:
        return "tool_router"
    if low in COMPONENTS:
        return low
    if low in _ALIASES:
        return _ALIASES[low]
    for k, v in _ALIASES.items():
        if k in low:
            return v
    return "tool_router"


class JevTrace:
    """Langfuse-like tracer — holds run_id + step counter, batch POST, @observe decorator.

    Usage:
        tracer = JevTrace(host="http://localhost:8000", public_key="jt_pub_...", secret_key="jt_sec_...")
        @tracer.observe(name="my_func", component="planner")
        def my_func(x): return x
        with tracer.span("retriever", inputs={"q": q}):
            docs = retriever(q)
        tracer.flush(); tracer.shutdown()
    """

    def __init__(
        self,
        api_url: str | None = None,
        host: str | None = None,
        task_name: str = "agent-task",
        api_key: str | None = None,
        public_key: str | None = None,
        secret_key: str | None = None,
        project: str | None = None,
        flush_at: int = 10,
        flush_interval: float = 2.0,
    ):
        import os as _os

        # Langfuse-style env fallback
        host = host or api_url or _os.getenv("JEVTRACE_HOST") or _os.getenv("LANGFUSE_HOST") or _os.getenv("JEVTRACE_API_URL") or "http://localhost:8000"
        self.api_url = host.rstrip("/")
        self.task_name = task_name or _os.getenv("JEVTRACE_TASK") or "agent-task"
        public_key = public_key or _os.getenv("JEVTRACE_PUBLIC_KEY") or _os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = secret_key or _os.getenv("JEVTRACE_SECRET_KEY") or _os.getenv("LANGFUSE_SECRET_KEY")
        api_key = api_key or _os.getenv("JEV_API_KEY") or _os.getenv("TYPESAFE_API_KEY")
        self.public_key = public_key
        self.secret_key = secret_key
        self.headers = {"Content-Type": "application/json"}
        if public_key and secret_key:
            import base64

            tok = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
            self.headers["Authorization"] = f"Basic {tok}"
        elif api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.run_id: str | None = None
        self._step = 0
        self._client = httpx.Client(timeout=5)
        # batch queue for Langfuse-style ingestion
        self._batch: list[dict] = []
        self._flush_at = flush_at
        self._flush_interval = flush_interval
        self._last_flush = time.time()
        self._project = project

    def _ensure_run(self):
        if self.run_id:
            return
        if self.public_key:
            # Langfuse-like: generate run_id locally and queue trace-create
            self.run_id = str(uuid.uuid4())
            self._batch.append({"type": "trace-create", "body": {"id": self.run_id, "name": self.task_name, "project": self._project}})
            if len(self._batch) >= self._flush_at:
                self.flush()
            return
        r = self._client.post(f"{self.api_url}/api/v1/runs", json={"task_name": self.task_name}, headers=self.headers)
        r.raise_for_status()
        self.run_id = r.json()["id"]

    def _post_step(self, component: str, status: str, inputs: dict | None, outputs: dict | None, latency_ms: int | None):
        self._ensure_run()
        self._step += 1
        comp = normalize_component(component)
        payload = {
            "step_number": self._step,
            "component": comp,
            "status": status,
            "input": inputs or {},
            "output": outputs or {},
            "latency_ms": latency_ms,
        }
        # Use batch queue if public_key set (Langfuse-like), else immediate POST
        if self.public_key:
            self._batch.append({"type": "observation-create", "body": {"runId": self.run_id, "step_number": self._step, "component": comp, "status": status, "input": inputs or {}, "output": outputs or {}, "latency_ms": latency_ms}})
            if len(self._batch) >= self._flush_at or (time.time() - self._last_flush) > self._flush_interval:
                self.flush()
        else:
            try:
                self._client.post(f"{self.api_url}/api/v1/runs/{self.run_id}/steps", json=payload, headers=self.headers).raise_for_status()
            except Exception:
                pass  # best-effort for demo; production should queue

    @contextmanager
    def span(self, component: str, inputs: dict | None = None, outputs: dict | None = None):
        start = time.time()
        try:
            yield
            latency = int((time.time() - start) * 1000)
            self._post_step(component, "success", inputs, outputs, latency)
        except Exception as exc:
            latency = int((time.time() - start) * 1000)
            self._post_step(component, "failed", inputs, {"error": str(exc)}, latency)
            raise

    def observe(self, name: str | None = None, component: str | None = None, as_type: str | None = None):
        """Decorator like Langfuse @observe — @tracer.observe(name='my_func', component='planner')."""
        import functools
        import inspect

        def _record(comp: str, nm: str, start: float, success: bool, result: Any = None, error: Exception | None = None):
            latency = int((time.time() - start) * 1000)
            if success:
                self._post_step(comp, "success", {"name": nm, "args": ""}, {"result": str(result)[:500] if result is not None else ""}, latency)
            else:
                self._post_step(comp, "failed", {"name": nm}, {"error": str(error) if error else ""}, latency)

        def decorator(fn):
            comp = component or "tool_router"
            nm = name or fn.__name__

            if inspect.iscoroutinefunction(fn):

                @functools.wraps(fn)
                async def aw(*args, **kwargs):
                    start = time.time()
                    try:
                        res = await fn(*args, **kwargs)
                        _record(comp, nm, start, True, res)
                        return res
                    except Exception as exc:
                        _record(comp, nm, start, False, error=exc)
                        raise

                return aw

            @functools.wraps(fn)
            def sw(*args, **kwargs):
                start = time.time()
                try:
                    res = fn(*args, **kwargs)
                    _record(comp, nm, start, True, res)
                    return res
                except Exception as exc:
                    _record(comp, nm, start, False, error=exc)
                    raise

            return sw

        return decorator

    # alias for LangSmith compat
    trace = observe

    async def aspan(self, component: str, inputs: dict | None = None):
        # For async code: use as `async with tracer.aspan(...):`
        class _A:
            def __init__(self, outer, comp, inp):
                self.outer = outer
                self.comp = comp
                self.inp = inp
                self.start = None

            async def __aenter__(self):
                self.start = time.time()
                return self

            async def __aexit__(self, exc_type, exc, tb):
                latency = int((time.time() - self.start) * 1000)
                status = "failed" if exc_type else "success"
                out = {"error": str(exc)} if exc else {}
                self.outer._post_step(self.comp, status, self.inp, out, latency)
                return False

        return _A(self, component, inputs)

    def complete(self, status: str = "failed"):
        if not self.run_id:
            return
        self.flush()
        try:
            self._client.post(f"{self.api_url}/api/v1/runs/{self.run_id}/complete", json={"status": status}, headers=self.headers)
        except Exception:
            pass

    def analyze(self):
        if not self.run_id:
            raise RuntimeError("No run to analyze")
        self.flush()
        r = self._client.post(f"{self.api_url}/api/v1/runs/{self.run_id}/analyze", headers=self.headers)
        r.raise_for_status()
        return r.json()

    def flush(self):
        if not self._batch:
            return
        batch = self._batch[:]
        self._batch.clear()
        self._last_flush = time.time()
        try:
            # Prefer batch ingestion if public_key set
            if self.public_key:
                self._client.post(f"{self.api_url}/api/public/ingestion", json={"batch": batch}, headers=self.headers).raise_for_status()
            else:
                # fallback: steps already POSTed individually, just flush batch as steps
                for evt in batch:
                    b = evt.get("body", {})
                    self._client.post(f"{self.api_url}/api/v1/runs/{b.get('runId')}/steps", json={"step_number": b.get("step_number"), "component": b.get("component"), "status": b.get("status"), "input": b.get("input"), "output": b.get("output"), "latency_ms": b.get("latency_ms")}, headers=self.headers)
        except Exception:
            # re-queue on failure (best-effort)
            self._batch.extend(batch)

    def shutdown(self):
        self.flush()
        self.close()

    def close(self):
        try:
            self.flush()
            self._client.close()
        except Exception:
            pass
