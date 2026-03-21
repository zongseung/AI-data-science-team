"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_data_science_team.api.v1.flows import router as flows_router
from ai_data_science_team.api.v1.health import router as health_router
from ai_data_science_team.api.v1.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    yield


app = FastAPI(
    title="AI Data Science Team",
    description="AI Financial Data Science Team API",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount routers
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(flows_router, prefix="/api/v1/flows", tags=["flows"])
app.include_router(ws_router, prefix="/api/v1", tags=["websocket"])
