"""Public support/contact endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.support_request import SupportRequest
from app.services.email_service import email_service


router = APIRouter(prefix="/support", tags=["support"])


class SupportContactRequest(BaseModel):
    """Payload for support contact form."""

    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    message: str = Field(..., min_length=5, max_length=5000)
    source: str | None = Field(default="site_footer", max_length=120)


class SupportContactResponse(BaseModel):
    """API response for support contact submissions."""

    success: bool
    message: str
    request_id: str


@router.post("/contact", response_model=SupportContactResponse)
async def submit_support_contact(
    payload: SupportContactRequest,
    session: AsyncSession = Depends(get_db),
) -> SupportContactResponse:
    """Store and notify a support request from public website."""
    request_row = SupportRequest(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        message=payload.message.strip(),
        source=payload.source,
        status="new",
    )
    session.add(request_row)
    await session.commit()
    await session.refresh(request_row)

    inbox = settings.support_inbox_email
    if inbox:
        subject = f"[Soporte] Nueva solicitud de {request_row.name}"
        body = (
            "Nueva solicitud de soporte\n\n"
            f"Nombre: {request_row.name}\n"
            f"Email: {request_row.email}\n"
            f"Origen: {request_row.source or 'n/a'}\n"
            f"ID: {request_row.id}\n\n"
            "Mensaje:\n"
            f"{request_row.message}\n"
        )
        await email_service.send_email(inbox, subject, body)

    return SupportContactResponse(
        success=True,
        message="Hemos recibido tu solicitud. Te contactaremos pronto.",
        request_id=str(request_row.id),
    )
