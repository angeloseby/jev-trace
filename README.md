# JevTrace — Agent Failure Intelligence Platform

LangSmith + Datadog + Jev. Collects multi-agent OpenTelemetry traces, runs them through Jev's `Choice`/`Score`/`Noul` (`POST /v1/systemone`) in parallel, and surfaces root cause, decisive step, severity, and repair recommendations.

## Quick Start

```bash
docker compose up           # postgres, redis, api, worker, dashboard
# API:      http://localhost:8000/docs    (/api/v1/*)
# Dashboard http://localhost:3000
# Mock Jev works without JEV_API_KEY; set it in .env for real attribution
```

Local dev without Docker:
```bash
# API
pip install -e apps/api -e packages/schemas -e packages/jev-client -e packages/trace-parser
uvicorn app.main:app --reload --app-dir apps/api  # or: cd apps/api && uvicorn app.main:app --reload

# Dashboard
cd apps/dashboard && npm install && npm run dev

# Worker
celery -A app.celery_app worker --loglevel=info --app-dir apps/worker
```

## API (versioned JSON-only, JWT)

| Route | Purpose |
|---|---|
| `POST /api/v1/auth/login` | JWT login |
| `POST /api/v1/runs` | Create run |
| `POST /api/v1/runs/{id}/steps` | Add step `{component, status, latency_ms}` |
| `POST /api/v1/runs/{id}/complete` | End run |
| `POST /api/v1/runs/{id}/analyze` | Normalize → Jev → persist attribution (202) |
| `GET  /api/v1/runs/{id}/attribution` | Get attribution |
| `GET  /api/v1/runs/{id}/graph` | Attribution graph `{nodes, edges}` |
| `POST/GET /api/v1/runs/{id}/recommendations` | Repair actions |
| `GET  /api/v1/analytics/{failures,components,trends}` | Dashboards |

Pagination is cursor-based (`?limit=20&cursor=...` → `{items, next_cursor, has_more}`). Standard envelope `{success,data,error}`.

## Project Layout

```
apps/api/        FastAPI — routers api/*.py, schemas/*, services/jev_service.py, db/models.py
apps/dashboard/  Next.js 14 + Tailwind + Recharts
apps/worker/     Celery (Redis broker)
packages/        jev-client, trace-parser, attribution, schemas, analytics
infra/           docker/*, terraform/*, k8s/*
tests/           unit | integration (mock Jev) | e2e
```

## Jev Integration

- Single call `POST /v1/systemone` with one `state` (normalized `{task, steps:[{component,status}]}`) + parallel `Choice` (component/category/repair), `Score` (severity), `Noul` (20+ causal hypotheses).
- Dashboard never calls Jev directly — go through `POST /internal/jev/analyze` → `app/services/jev_service.py`.
- Without `JEV_API_KEY`, `jev_service` falls back to deterministic mock — CI/tests don't need a live key.

## Docs

- Full spec: `project-plan.md` (API v1, Jev question sets, roadmap)
- Agent guide: `AGENTS.md`
