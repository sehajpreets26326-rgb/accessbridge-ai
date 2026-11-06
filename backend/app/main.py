"""FastAPI application entry point.

Run with:

    uvicorn backend.app.main:app --reload --port 8000

Or via the project root script:

    python -m backend.app.main
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routes import agents_router, dashboard_router, questions_router, review_router


logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger("accessbridge.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("AccessBridge AI starting — environment=%s", settings.environment)
    init_db()
    log.info("Database initialised at %s", settings.database_url)
    from .services.llm import switch_trust_status
    log.info("Switch Trust status: %s", switch_trust_status())
    yield
    log.info("AccessBridge AI shutting down.")


app = FastAPI(
    title="AccessBridge AI",
    description="Making essential information understandable and accessible to everyone.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(questions_router)
app.include_router(dashboard_router)
app.include_router(agents_router)
app.include_router(review_router)

# Switch bridge
from switch_integration import bridge_router  # noqa: E402
app.include_router(bridge_router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "environment": settings.environment,
        "docs": "/docs",
        "switch_health": "/switch/health",
    }


@app.get("/api/health", tags=["meta"])
def api_health() -> dict:
    from .services.llm import switch_trust_status
    from .integrations import mattermost
    return {
        "status": "ok",
        "environment": settings.environment,
        "switch_trust": switch_trust_status(),
        "mattermost": mattermost.status(),
        "database": settings.database_url,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=False)
