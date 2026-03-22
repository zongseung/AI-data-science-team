"""FastAPI application entrypoint."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Bootstrap sys.path so shared/* and collection-service/app/* are importable
_src = Path(__file__).resolve().parents[3]  # .../src/
for _pkg in ("shared", "collection-service/app"):
    _p = str(_src / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.v1.flows import router as flows_router
from app.v1.health import router as health_router
from app.v1.ws import router as ws_router

# Paths
_DIST = Path(__file__).resolve().parents[3] / "web-service" / "dist"
_INDEX = _DIST / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    yield


app = FastAPI(
    title="AI Data Science Team",
    description="AI Financial Data Science Team API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Mount routers
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(flows_router, prefix="/api/v1/flows", tags=["flows"])
app.include_router(ws_router, prefix="/api/v1", tags=["websocket"])

# Serve built frontend assets (only when dist/ exists after `npm run build`)
if (_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

if _INDEX.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Return index.html for all non-API routes (SPA client-side routing)."""
        return FileResponse(str(_INDEX))
