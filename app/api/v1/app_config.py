"""Application bootstrap configuration endpoints."""

from fastapi import APIRouter

from app.config import settings
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
