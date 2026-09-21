import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded

from app.api import analytics, attributions, auth, ingest, internal, otlp, projects, recommendations, runs, steps
from app.core.config import settings as _settings
from app.core.limiter import limiter

app = FastAPI(title="JevTrace API", version="0.1.0")
app.state.limiter = limiter
# Update limiter default from settings
limiter._default_limits = [f"{_settings.rate_limit_per_minute}/minute"]

# OpenTelemetry instrumentation (optional — no-op if OTel not configured)
try:
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_TRACES_EXPORTER"):
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        trace.set_tracer_provider(TracerProvider())
        otlp = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
        trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp))
        FastAPIInstrumentor.instrument_app(app)
except Exception:
    pass

origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
try:
    from slowapi.middleware import SlowAPIMiddleware

    app.add_middleware(SlowAPIMiddleware)
except Exception:
    pass

# Versioned API — spec requires /api/v1/*

@app.get("/health")
async def health():
    return {"status": "ok"}


# Standard envelope error handler (spec: {success, error:{code,message}})
@app.exception_handler(Exception)
async def _envelope_errors(request: Request, exc: Exception):
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "data": None, "error": {"code": str(exc.status_code), "message": str(exc.detail)}},
        )
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_envelope(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"success": False, "data": None, "error": {"code": "RATE_LIMITED", "message": f"Rate limit exceeded: {exc.detail}"}},
        headers={"Retry-After": str(exc.detail.split()[-1])} if hasattr(exc, "detail") else {},
    )


# Pydantic validation → envelope with valid components hint
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def _validation_envelope(request: Request, exc: RequestValidationError):
    # Surface valid components for step errors
    detail = exc.errors()
    msg = str(detail[0].get("msg", "")) if detail else str(exc)
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": msg,
                "details": {
                    "errors": detail,
                    "valid_components": ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"],
                    "hints": {"llm": "generator", "search": "retriever", "tool": "tool_router", "api": "external_api", "chain": "planner"},
                },
            },
        },
    )


# Register routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(steps.router, prefix="/api/v1")
app.include_router(attributions.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(otlp.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api")
app.include_router(internal.router)
