"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.chat.conversation import RedisConversationStore
from app.chat.router import router as chat_router
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, register_exception_handlers
from app.datasets.router import router as datasets_router
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.dependencies import get_settings
from app.llm.factory import create_llm_client
from app.query.router import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    # Initialize DuckDB
    db = DuckDBManager()
    await db.startup(settings.DUCKDB_PATH)
    app.state.db = db

    # Initialize metadata store
    metadata_store = MetadataStore(db)
    await metadata_store.create_table()
    app.state.metadata_store = metadata_store

    # Initialize LLM client
    app.state.llm_client = create_llm_client(settings)

    # Initialize Redis + conversation store
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis_client
    app.state.conversation_store = RedisConversationStore(
        redis_client, ttl_hours=settings.CONVERSATION_TTL_HOURS
    )

    yield

    # Shutdown
    await redis_client.aclose()
    await db.shutdown()


app = FastAPI(
    title="data-rag",
    description="Natural language queries over structured CSV data using Text-to-SQL with DuckDB",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)
app.include_router(datasets_router)
app.include_router(query_router)
app.include_router(chat_router)


templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
    """Serve the chat interface."""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/panel", response_class=HTMLResponse)
async def admin_panel(request: Request) -> HTMLResponse:
    """Serve the admin panel."""
    return templates.TemplateResponse("admin.html", {"request": request})
