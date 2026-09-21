# JevTrace — Agent Failure Intelligence Platform

[![PyPI version](https://img.shields.io/pypi/v/jev-trace.svg)](https://pypi.org/project/jev-trace/0.1.0/)
[![Python](https://img.shields.io/pypi/pyversions/jev-trace.svg)](https://pypi.org/project/jev-trace/0.1.0/)

LangSmith + Datadog + Jev. Collects multi-agent traces (manual, LangChain, or OpenTelemetry), runs them through Jev's `Choice`/`Score`/`Noul` (`POST /v1/systemone` via `typesafe-sdk`) in parallel, and surfaces root cause, decisive step, severity, and repair recommendations.

> `jev-trace 0.1.0` is **live on PyPI** — `pip install jev-trace` works out of the box, no local build needed.

## 3-line integration — like Langfuse

```bash
pip install jev-trace
# LangChain: pip install jev-trace[langchain]
```
```python
from jev_trace import JevTrace
tracer = JevTrace(host="http://localhost:8000", task_name="my-agent")  # or JEVTRACE_HOST env
with tracer.span("retriever", inputs={"query": q}):
    docs = retriever(q)
tracer.complete("failed"); tracer.analyze()  # Jev parallel Choice/Score/Noul
# decorator:
@tracer.observe(component="planner")
def my_planner(x): return plan(x)
```

**LangChain/LangGraph:**
```python
from jev_trace import JevTrace
from jev_trace.langchain import JevTraceCallbackHandler
tracer = JevTrace(host="http://localhost:8000")
handler = JevTraceCallbackHandler(tracer)
llm = ChatOpenAI(callbacks=[handler])
chain = prompt | llm
chain.invoke({"input": "…"}, config={"callbacks": [handler]})
```

**OTel zero-code:** `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python my_agent.py` → `otel-collector` → `POST /api/v1/otlp/traces` auto-maps `llm→generator`, `search→retriever`.

**Multi-tenant (Langfuse-like):** Dashboard `http://localhost:3000/settings` → create project → `Generate jt_pub_/jt_sec_` → use as `JevTrace(public_key="jt_pub_…", secret_key="jt_sec_…")` or `Authorization: Basic base64(pub:sec)` for `POST /api/public/ingestion` batch.

## Quick Start

```bash
cp .env.example .env  # set JEV_API_KEY (or TYPESAFE_API_KEY) — required, no mocking
docker compose up -d --wait  # postgres, redis, otel-collector:4317/4318, api:8000, worker, dashboard:3000
docker compose exec api alembic upgrade head  # or auto via Dockerfile gunicorn entrypoint
python scripts/seed.py  # 3 demo traces → dashboard
# API:      http://localhost:8000/docs    (/api/v1/*)
# Dashboard http://localhost:3000  (Runs → /runs/[id] → Analytics → Settings)
```

Local dev without Docker:
```bash
pip install -e apps/api -e packages/tracer -e packages/jev-client -e packages/trace-parser -e packages/schemas
uvicorn app.main:app --reload --app-dir apps/api
cd apps/dashboard && npm install && npm run dev  # :3000
celery -A app.celery_app worker --loglevel=info --app-dir apps/worker
```

## API (versioned JSON-only, cursor pagination, envelope `{success,data,error}`)

| Route | Purpose |
|---|---|
| `POST /api/v1/auth/login` | JWT login (demo `angelo@example.com`/`secret`; `REQUIRE_AUTH=false` by default) |
| `POST /api/v1/projects` / `POST /api/v1/projects/{id}/api-keys` | Multi-tenant projects & `jt_pub_/jt_sec_` keys |
| `POST /api/v1/runs` | Create run `{task_name}` → `201 {id, project_id}` |
| `POST /api/v1/runs/{id}/steps` | Add step `{step_number, component: planner|retriever|tool_router|memory|generator|verifier|external_api (aliases: llm→generator etc), status, input, output, latency_ms}` |
| `POST /api/v1/runs/{id}/complete` | End run `{status: failed|completed}` → auto `failures` row |
| `POST /api/v1/runs/{id}/analyze` | Normalize `{task, steps:[{component,status}]}` → Jev SDK `Choice/Score/Noul` parallel (202, rate `10/min`) |
| `GET  /api/v1/runs/{id}/attribution` | `responsible_component` + `failure_step` + `failure_category` + `severity` |
| `GET  /api/v1/runs/{id}/graph` | `{nodes:[{id,weight}], edges}` causal weights |
| `POST/GET /api/v1/runs/{id}/recommendations` | Repair `increase_top_k|add_reranker|...` |
| `POST /api/public/ingestion` / `POST /api/v1/ingest` | Batch `{"batch":[{"type":"trace-create","body":{"id","name"}}, {"type":"observation-create","body":{"traceId","component":"llm"}}]}` Basic auth `jt_pub:jt_sec` |
| `POST /api/v1/otlp/traces` | OTLP JSON `resourceSpans` → Runs/Steps |
| `GET  /api/v1/analytics/{failures,components,trends}` | Dashboards (`failures` GROUP BY, `components` 1-fail/total, `trends` by date) |

Pagination cursor (`?limit=20&cursor=ey...` → `{items, next_cursor, has_more}`) via `base64({id,ts})` for runs, `base64({n,id})` for steps. Validation `422` envelope includes `details:{valid_components:[...], hints:{llm:"generator"}}`.

## Project Layout

```
apps/api/        FastAPI — app/main.py (CORS env, rate 60/min 429, OTel, envelope), routers api/*.py, schemas/*, services/jev_service.py (typesafe_sdk), db/models.py (projects/api_keys/runs/steps hierarchy)
apps/dashboard/  Next.js 14 + Tailwind + Recharts — src/app/runs (cursor+search/status filter), src/app/runs/[id] (trace+attribution+graph), src/app/analytics (Bar/Pie/Line), src/app/components, src/app/graph, src/app/settings (projects/keys)
apps/worker/     Celery — app/celery_app.py (analyze_run asyncio, retries)
packages/tracer/ jev-trace SDK — JevTrace span/@observe, LangChain handler, batch queue (httpx)
packages/        jev-client (typesafe wrapper), trace-parser (normalize), attribution (graph), schemas, analytics
infra/           docker/* (api gunicorn+healthcheck+non-root, worker, dashboard + otel-collector:4317/4318), k8s/, terraform (placeholders)
tests/           unit (jev mock/live, normalizer) | integration (api→DB, projects+alias, smoke) | e2e (Jev live, 503 skip)
```

## Jev Integration

- Single call `POST /v1/systemone` via `AsyncTypeSafeClient` `model=jev-latest` with one `state` (normalized `{task, steps}`) + parallel `Choice` (component/category/repair), `Score` (severity Low/Med/High/Critical), `Noul` (7 causal `*_caused_failure`).
- Dashboard never calls Jev directly — go through `POST /internal/jev/analyze`/`POST /runs/{id}/analyze` → `app/services/jev_service.py`.
- `JEV_API_KEY`/`TYPESAFE_API_KEY` required (`RuntimeError` if missing, no mock fallback) — set in `.env` (`JEV_API_KEY=apikey_...` for `api.typesafe.ai`).

## Docs

- Full spec: `project-plan.md` (API v1, Jev question sets, roadmap)
- Pending work: `ROADMAP.md` (PyPI ✅, Who&When Pro eval, replay engine, prod infra)
- Integration: `docs/integration.md` (3-line, LangChain, OTel, manual REST, publishing)
- Agent guide: `AGENTS.md`
- Benchmark: `scripts/benchmark_whowhen.py --input data/whowhen_pro.jsonl` (Who/When/Error F1/Joint)
