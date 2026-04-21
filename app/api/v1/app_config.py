"""Application bootstrap configuration endpoints."""

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.auth import AppConfigResponse


router = APIRouter(prefix="/app", tags=["app"])


@router.get("/config", response_model=AppConfigResponse)
async def get_app_config() -> AppConfigResponse:
    """Return public client bootstrap configuration."""
    return AppConfigResponse(
        app_name=settings.api_title,
        version=settings.api_version,
        environment=settings.environment,
        features={
            "email_verification": True,
            "password_reset": True,
            "otp": True,
            "ocr": settings.ocr_enabled,
            "storage_r2": settings.storage_backend == "r2",
        },
    )


@router.get("/cors-diagnostics")
async def get_cors_diagnostics(
    request: Request,
    _: User = Depends(require_roles("platform_admin")),
) -> dict:
    """Return CORS diagnostics for troubleshooting from trusted admin clients."""
    origin = request.headers.get("origin")
    return {
        "environment": settings.environment,
        "request_origin": origin,
        "allowed": settings.is_allowed_origin(origin),
        "configured_origins": settings.cors_origins,
        "configured_origins_count": len(settings.cors_origins),
    }
