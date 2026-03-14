"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, register_exception_handlers
from app.dependencies import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    yield


app = FastAPI(
    title="data-rag",
    description="Natural language queries over structured CSV data using Text-to-SQL with DuckDB",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
