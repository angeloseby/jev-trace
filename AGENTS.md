# AGENTS.md — JevTrace

## Source of Truth
- `project-plan.md` is the complete spec (architecture, data model, API v1, Jev question sets, 7-phase roadmap). Read the relevant section before coding; don't reinvent contracts.
- Monorepo is initialized — see layout below. Trust `docker-compose.yml`, `apps/*/pyproject.toml`, `apps/dashboard/package.json`, `.github/workflows/ci.yml` as executable truth over docs if they conflict.

## Monorepo Layout (do not rename/move these)
```
apps/api/        # FastAPI — app/main.py, app/api/*.py, app/schemas/*, app/services/jev_service.py, app/db/models.py, alembic/
apps/dashboard/  # Next.js 14 + Tailwind + Recharts — src/app/*, src/lib/api.ts
apps/worker/     # Celery — app/celery_app.py
packages/        # jev-client, trace-parser, attribution, schemas, analytics (hatchling)
infra/docker/    # Dockerfile.api/.worker/.dashboard
infra/terraform/ infra/k8s/  # placeholders
tests/unit|integration|e2e/  scripts/ docs/
```

## Stack & Commands
- Backend: FastAPI + SQLAlchemy[asyncio]+asyncpg + Alembic + Redis + Celery (`apps/api/pyproject.toml`)
- Frontend: Next.js 14 + Tailwind + Recharts (`apps/dashboard/package.json:14`)
- Tooling: `docker compose up` (postgres, redis, api :8000, worker, dashboard :3000), `uvicorn app.main:app --reload --app-dir apps/api`, `alembic upgrade head` (from `apps/api`), `celery -A app.celery_app worker --app-dir apps/worker`, `npm run dev|build` in `apps/dashboard`, `pytest tests/unit tests/integration -q`, `ruff check apps/ packages/`
- Env: `.env.example` → `.env` (`DATABASE_URL`, `REDIS_URL`, `JEV_API_KEY` — mock fallback if unset)

## API Conventions (from spec — follow exactly)
- Versioned JSON-only: `Content-Type: application/json`, routes `/api/v1/*`
- Auth: JWT `Authorization: Bearer <token>`; `POST /api/v1/auth/login` + `/auth/refresh`
- Pagination: cursor-based (`?limit=20&cursor=...` → `{items, next_cursor, has_more}`), not offset — required for trace datasets
- Standard envelope: `{success, data, error: {code, message, details}}`; status codes 200/201/202/400/401/403/404/409/422/429/500
- Key routes: `POST /runs`, `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/complete`, `POST /runs/{id}/steps`, `GET /runs/{id}/steps`, `POST /runs/{id}/analyze`, `GET /runs/{id}/attribution`, `GET /runs/{id}/graph`, `POST|GET /runs/{id}/recommendations`, `GET /analytics/{failures,components,trends}`

## Data Model — Use These Names Verbosely
- `runs(id UUID, status: running|completed|failed, task_name, started_at, ended_at, total_steps)`
- `steps(id UUID, run_id UUID, step_number INT, component VARCHAR(50), input JSONB, output JSONB, status, latency_ms, created_at)`
- `attributions(run_id, responsible_component, component_confidence, failure_step INT, failure_category, category_confidence, severity FLOAT)`
- `recommendations(run_id, recommendation, confidence)` and `failures(run_id, failure_detected, reason, severity_score)`
- Component enum (exact strings): `planner`, `retriever`, `tool_router`, `memory`, `generator`, `verifier`, `external_api`
- Failure categories (exact): `planning_error`, `retrieval_error`, `tool_failure`, `memory_failure`, `hallucination`, `timeout`, `verification_failure`
- Repair actions: `increase_top_k`, `add_reranker`, `improve_embeddings`, `retry_api`, `enable_citations`, `human_review`/`add_human_review`

## Jev Attribution Engine — Non-Obvious
- Single endpoint `POST /v1/systemone` takes one `state` (normalized trace) + multiple questions in parallel. Don't call Jev per-question sequentially.
- Three primitives to use together: `Choice` (responsible_component, failure_category, repair), `Score` (severity 0-? with rubric Low/Medium/High/Critical), `Noul` (20+ causal hypotheses like `retrieval_caused_failure: 0.93`).
- Trace normalizer must convert raw steps into `{task, steps: [{component, status}]}` before Jev — this is the Jev input `state`.
- Dashboard must never call Jev directly; go through internal `POST /internal/jev/analyze` service (`app/services/jev_service.py`).
- Attribution graph is the differentiator: store per-component weights `{planner: 0.14, retriever: 0.91, generator: 0.31}`, not just a single label.

## Workflow Gotchas
- No build/test/lint/typecheck configured yet. When you add them, document exact commands here and prefer executable config over prose.
- Mock Jev in integration/E2E tests (`API → DB`, `API → Jev`, `Worker → DB`); don't require live Jev key for CI.
- Phases are sequential: trace collection → failure detection → normalization → Jev engine → graph → recommendations → dashboard → Who&When/Who&When Pro benchmarking. Don't skip normalization when implementing attribution.
- Benchmark target is `Who&When Pro` (12k+ labeled trajectories, metrics: Who/When/Error F1/Joint Accuracy) — keep schemas compatible.
- After editing `AGENTS.md` verify `docker compose config --quiet` and `pytest tests/unit tests/integration -q` still pass; don't break the happy path.
