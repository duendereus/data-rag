"""Middleware for request tracking and global exception handling."""

import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    DatasetNotFoundError,
    FileTooLargeError,
    LLMError,
    NoDatasetsAvailableError,
    QueryExecutionError,
    SchemaExtractionError,
    UnsupportedFileTypeError,
)

logger = structlog.get_logger()

EXCEPTION_STATUS_MAP: dict[type[Exception], int] = {
    DatasetNotFoundError: 404,
    NoDatasetsAvailableError: 404,
    UnsupportedFileTypeError: 422,
    FileTooLargeError: 413,
    QueryExecutionError: 422,
    LLMError: 502,
    SchemaExtractionError: 500,
}


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique X-Request-ID header to every request and response."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        """Inject request ID into headers and structlog context."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that map custom exceptions to HTTP responses."""

    @app.exception_handler(DatasetNotFoundError)
    @app.exception_handler(NoDatasetsAvailableError)
    @app.exception_handler(UnsupportedFileTypeError)
    @app.exception_handler(FileTooLargeError)
    @app.exception_handler(QueryExecutionError)
    @app.exception_handler(LLMError)
    @app.exception_handler(SchemaExtractionError)
    async def handle_custom_exception(request: Request, exc: Exception) -> JSONResponse:
        status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
        detail = {"error": type(exc).__name__, "message": str(exc)}

        if isinstance(exc, QueryExecutionError):
            detail["sql"] = exc.sql

        logger.error(
            "request_error",
            error_type=type(exc).__name__,
            detail=str(exc),
            status_code=status_code,
            path=request.url.path,
        )

        return JSONResponse(status_code=status_code, content=detail)
