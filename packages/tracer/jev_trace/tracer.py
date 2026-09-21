"""Core tracer — auto-creates runs/steps with background POST."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager, asynccontextmanager
from typing import Any

import httpx

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
    # fuzzy: closest match for UX hint
    import difflib

    m = difflib.get_close_matches(low, COMPONENTS, n=1, cutoff=0.6)
    return m[0] if m else "tool_router"


class JevTrace:
    """Minimal tracer — holds run_id + step counter, POSTs in background."""

    def __init__(self, api_url: str = "http://localhost:8000", task_name: str = "agent-task", api_key: str | None = None):
        self.api_url = api_url.rstrip("/")
        self.task_name = task_name
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.run_id: str | None = None
        self._step = 0
        self._client = httpx.Client(timeout=5)

    def _ensure_run(self):
        if self.run_id:
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
        try:
            self._client.post(f"{self.api_url}/api/v1/runs/{self.run_id}/complete", json={"status": status}, headers=self.headers)
        except Exception:
            pass

    def analyze(self):
        if not self.run_id:
            raise RuntimeError("No run to analyze")
        r = self._client.post(f"{self.api_url}/api/v1/runs/{self.run_id}/analyze", headers=self.headers)
        r.raise_for_status()
        return r.json()

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
