from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, attributions, auth, internal, recommendations, runs, steps

app = FastAPI(title="JevTrace API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Versioned API — spec requires /api/v1/*

@app.get("/health")
async def health():
    return {"status": "ok"}


# Register routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(steps.router, prefix="/api/v1")
app.include_router(attributions.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(internal.router)
