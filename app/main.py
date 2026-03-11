"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.config import settings
from app.core.exceptions import AppException
from app.db.session import close_db, init_db
from app.services.ocr_service import initialize_ocr, close_ocr


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and close shared application resources."""
    # Initialize database
    await init_db()

    # Initialize OCR engine if enabled
    if settings.ocr_enabled:
        try:
            initialize_ocr()
        except Exception as e:
            logging.warning(f"OCR initialization failed, continuing without OCR: {e}")

    yield

    # Shutdown
    await close_db()
    close_ocr()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}


@app.exception_handler(AppException)
async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
    """Map domain exceptions to a consistent API response."""
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code in {"UNAUTHORIZED", "INVALID_TOKEN"}:
        status_code = status.HTTP_401_UNAUTHORIZED
    elif exc.code in {"FORBIDDEN"}:
        status_code = status.HTTP_403_FORBIDDEN
    elif exc.code in {"NOT_FOUND", "USER_NOT_FOUND"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {"CONFLICT", "EMAIL_ALREADY_EXISTS"}:
        status_code = status.HTTP_409_CONFLICT

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )
