"""
Global exception handlers for FastAPI.

Maps domain/application exceptions to proper HTTP responses
and provides a catch-all handler for unhandled errors.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Domain exceptions ────────────────────────────────────────────────────────

class CodeIntelError(Exception):
    """Base exception for all CodeIntel domain errors."""

    def __init__(self, message: str = "An internal error occurred", code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(CodeIntelError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        message = f"{resource} not found: {identifier}".strip(": ") if identifier else (
            resource if "not found" in resource.lower() else f"{resource} not found"
        )
        super().__init__(
            message=message,
            code="NOT_FOUND",
        )


class ValidationError(CodeIntelError):
    """Raised when input validation fails at the domain level."""

    def __init__(self, message: str):
        super().__init__(message=message, code="VALIDATION_ERROR")


class IngestionError(CodeIntelError):
    """Raised when repository ingestion fails."""

    def __init__(self, message: str):
        super().__init__(message=message, code="INGESTION_ERROR")


class RateLimitError(CodeIntelError):
    """Raised when external API rate limit is hit."""

    def __init__(self, service: str = "GitHub"):
        super().__init__(
            message=f"{service} rate limit exceeded. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
        )


class ExternalServiceError(CodeIntelError):
    """Raised when an external service (GitHub, LLM) is unreachable or errors."""

    def __init__(self, service: str, detail: str = ""):
        super().__init__(
            message=f"External service error ({service}): {detail}",
            code="EXTERNAL_SERVICE_ERROR",
        )


# Aliases for backwards and alternative naming compatibility
ValidationException = ValidationError
IngestionException = IngestionError
NotFoundException = NotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": exc.code, "message": exc.message, "detail": exc.message},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(_request: Request, exc: ValidationError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.code, "message": exc.message, "detail": exc.message},
        )

    @app.exception_handler(IngestionError)
    async def ingestion_handler(_request: Request, exc: IngestionError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(_request: Request, exc: RateLimitError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(
        _request: Request, exc: ExternalServiceError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> ORJSONResponse:
        logger.exception("Unhandled exception", error=str(exc))
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            },
        )
