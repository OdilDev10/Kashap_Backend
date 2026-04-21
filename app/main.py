"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import Any
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1 import api_router
from app.config import settings
from app.core.exceptions import AppException
from app.db.session import close_db, init_db
from app.services.ocr_service import initialize_ocr, close_ocr
from app.services.startup_seed import run_startup_seed
from app.middleware.audit import AuditMiddleware

logger = logging.getLogger("app.http")
logger.setLevel(logging.INFO)

limiter = Limiter(key_func=get_remote_address)


def _build_error_response(
    code: str, message: str, detail: Any = None
) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
    }


def _status_code_to_error_code(status_code: int) -> str:
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "VALIDATION_ERROR"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "UNAUTHORIZED"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "FORBIDDEN"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "NOT_FOUND"
    if status_code == status.HTTP_409_CONFLICT:
        return "CONFLICT"
    if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return "VALIDATION_ERROR"
    return "INTERNAL_ERROR"


def _normalize_http_exception_detail(
    status_code: int,
    detail: Any,
) -> tuple[str, str, Any]:
    default_code = _status_code_to_error_code(status_code)
    default_message = (
        "Error de validación"
        if status_code
        in {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}
        else "Solicitud inválida"
    )

    if isinstance(detail, dict):
        if detail.get("success") is False and isinstance(detail.get("error"), dict):
            error_obj = detail.get("error", {})
            return (
                str(error_obj.get("code") or default_code),
                str(error_obj.get("message") or default_message),
                error_obj.get("detail"),
            )
        return (
            str(detail.get("code") or default_code),
            str(detail.get("message") or default_message),
            detail.get("detail"),
        )

    if isinstance(detail, list):
        return default_code, default_message, detail

    if isinstance(detail, str) and detail.strip():
        return default_code, detail, None

    return default_code, default_message, None


def _apply_cors_headers(request: Request, response: Response) -> Response:
    origin = request.headers.get("origin")
    if settings.is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = str(origin)
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and close shared application resources."""
    # Initialize database
    await init_db()
    if settings.enable_startup_seed:
        await run_startup_seed()

    # Initialize OCR engine if enabled
    if settings.ocr_enabled:
        try:
            initialize_ocr()
        except Exception as exc:
            if settings.ocr_required:
                raise
            logger.warning(
                "OCR initialization warning (continuing without OCR): %s",
                exc,
            )
            logger.warning(
                "OCR features will be disabled. This is expected in CPU-only environments."
            )

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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def cors_safety_net(request: Request, call_next):
    """Ensure CORS headers are applied consistently, including failures."""
    origin = request.headers.get("origin")
    is_api_request = request.url.path.startswith("/api/")
    requested_method = request.headers.get("access-control-request-method")

    if request.method == "OPTIONS" and requested_method:
        if settings.is_allowed_origin(origin):
            response = Response(status_code=status.HTTP_200_OK)
            request_headers = request.headers.get("access-control-request-headers")
            response.headers["Access-Control-Allow-Methods"] = (
                "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                request_headers if request_headers else "*"
            )
            return _apply_cors_headers(request, response)
        if origin and is_api_request:
            logger.warning(
                "CORS preflight denied: origin=%s method=%s path=%s",
                origin,
                requested_method,
                request.url.path,
            )
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled pipeline exception before response generation")
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="Error interno del servidor",
                detail=None,
            ),
        )

    if origin and is_api_request and not settings.is_allowed_origin(origin):
        logger.warning(
            "CORS origin denied: origin=%s method=%s path=%s",
            origin,
            request.method,
            request.url.path,
        )

    return _apply_cors_headers(request, response)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP method, path, status and latency for each request."""
    started_at = perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "%s %s -> 500 (%.1fms)",
            request.method,
            request.url.path,
            duration_ms,
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="Error interno del servidor",
                detail=None,
            ),
        )
        return _apply_cors_headers(request, response)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}


@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
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

    response = JSONResponse(
        status_code=status_code,
        content=_build_error_response(
            code=exc.code,
            message=exc.message,
            detail=None,
        ),
    )
    return _apply_cors_headers(request, response)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Normalize FastAPI HTTPException to a single error contract."""
    code, message, detail = _normalize_http_exception_detail(
        exc.status_code, exc.detail
    )
    response = JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(code=code, message=message, detail=detail),
    )
    return _apply_cors_headers(request, response)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Normalize request body/query/path validation errors."""
    issues = []
    for err in exc.errors():
        loc_parts = [str(part) for part in err.get("loc", [])]
        field = ".".join(loc_parts[1:]) if len(loc_parts) > 1 else ".".join(loc_parts)
        issues.append(
            {
                "field": field or "body",
                "message": err.get("msg", "Error de validación"),
                "type": err.get("type", "validation_error"),
            }
        )

    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(
            code="VALIDATION_ERROR",
            message="Error de validación",
            detail=issues,
        ),
    )
    return _apply_cors_headers(request, response)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Fallback error handler to avoid leaking unstructured 500 errors."""
    logger.exception("Unhandled exception: %s", exc)
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="Error interno del servidor",
            detail=None,
        ),
    )
    return _apply_cors_headers(request, response)
