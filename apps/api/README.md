# JevTrace API

FastAPI service — trace collection, Jev attribution, and analytics.

```
uvicorn app.main:app --reload --port 8000
alembic upgrade head
```

Env: `DATABASE_URL`, `REDIS_URL`, `JEV_API_KEY` (mock fallback if unset).
