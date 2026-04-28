"""Support endpoints."""

import json
import uuid
from datetime import datetime
from typing import Any, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.support_request import SupportRequest
from app.models.user import User
from app.services.email_service import email_service
from app.services.storage_service import storage_service


router = APIRouter(prefix="/support", tags=["support"])


class SupportContactRequest(BaseModel):
    """Payload for support contact form."""

    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    subject: str | None = Field(default=None, min_length=3, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=80)
    message: str = Field(..., min_length=5, max_length=5000)
    attachments: list[str] = Field(default_factory=list, max_length=8)
    context: dict[str, Any] | None = None
    source: str | None = Field(default="site_footer", max_length=120)


class SupportContactResponse(BaseModel):
    """API response for support contact submissions."""

    success: bool
    message: str
    request_id: str


class SupportRequestListItem(BaseModel):
    id: str
    name: str
    email: str
    subject: str | None
    phone: str | None
    category: str | None
    message: str
    attachments: list[str]
    status: str
    source: str | None
    user_id: str | None
    created_at: datetime | None
    updated_at: datetime | None


class SupportRequestListResponse(BaseModel):
    items: list[SupportRequestListItem]
    total: int
    skip: int
    limit: int


class SupportStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(new|in_review|resolved|closed)$")


class SupportStatusUpdateResponse(BaseModel):
    success: bool
    message: str
    item: SupportRequestListItem


class SupportAttachmentResponse(BaseModel):
    success: bool
    file_path: str
    file_name: str
    mime_type: str
    file_size: int


ALLOWED_ATTACHMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/attachments", response_model=SupportAttachmentResponse)
async def upload_support_attachment(
    file: Annotated[UploadFile, File(...)],
) -> SupportAttachmentResponse:
    """Upload a support/report attachment and return storage path."""
    if file.content_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Tipo de archivo no permitido. Usa PDF, JPG, PNG o DOC/DOCX."
            ),
        )

    file_content = await file.read()
    file_size = len(file_content)
    if file_size > MAX_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo excede 10MB.",
        )

    extension = ""
    if file.filename and "." in file.filename:
        extension = "." + file.filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4()}{extension}"
    file_path = await storage_service.upload(
        file_content=file_content,
        file_name=unique_name,
        folder="support_reports",
    )
    return SupportAttachmentResponse(
        success=True,
        file_path=file_path,
        file_name=file.filename or unique_name,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
    )


@router.post("/contact", response_model=SupportContactResponse)
async def submit_support_contact(
    payload: SupportContactRequest,
    session: AsyncSession = Depends(get_db),
) -> SupportContactResponse:
    """Store and notify a support request from public website."""
    clean_subject = payload.subject.strip() if payload.subject else None
    clean_phone = payload.phone.strip() if payload.phone else None
    clean_category = payload.category.strip().lower() if payload.category else None
    attachments = [a.strip() for a in payload.attachments if a and a.strip()]
    context_payload = payload.context if payload.context else None

    if clean_category == "identity_theft":
        image_count, document_count = _count_attachment_types(attachments)
        if document_count < 1 or image_count < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Para reportar robo de identidad debes adjuntar al menos "
                    "1 documento y 2 imágenes."
                ),
            )

    request_row = SupportRequest(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        subject=clean_subject,
        phone=clean_phone,
        category=clean_category,
        message=payload.message.strip(),
        attachments_json=json.dumps(attachments) if attachments else None,
        context_json=json.dumps(context_payload) if context_payload else None,
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
            f"Asunto: {request_row.subject or 'n/a'}\n"
            f"Categoría: {request_row.category or 'n/a'}\n"
            f"Teléfono: {request_row.phone or 'n/a'}\n"
            f"Origen: {request_row.source or 'n/a'}\n"
            f"ID: {request_row.id}\n\n"
            "Mensaje:\n"
            f"{request_row.message}\n"
        )
        if attachments:
            body += "\nAdjuntos:\n" + "\n".join(attachments) + "\n"
        await email_service.send_email(inbox, subject, body)

    return SupportContactResponse(
        success=True,
        message="Hemos recibido tu solicitud. Te contactaremos pronto.",
        request_id=str(request_row.id),
    )


@router.get("/requests", response_model=SupportRequestListResponse)
async def list_support_requests(
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    status: str | None = None,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> SupportRequestListResponse:
    """Admin list of support requests with filters."""
    filters = []

    if status:
        filters.append(SupportRequest.status == status)

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                SupportRequest.name.ilike(term),
                SupportRequest.email.ilike(term),
                SupportRequest.subject.ilike(term),
                SupportRequest.category.ilike(term),
                SupportRequest.message.ilike(term),
            )
        )

    count_stmt = select(func.count(SupportRequest.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await session.execute(count_stmt)).scalar() or 0

    list_stmt = select(SupportRequest).order_by(SupportRequest.created_at.desc())
    if filters:
        list_stmt = list_stmt.where(*filters)
    list_stmt = list_stmt.offset(skip).limit(limit)

    rows = (await session.execute(list_stmt)).scalars().all()
    items = [
        SupportRequestListItem(
            id=str(row.id),
            name=row.name,
            email=row.email,
            subject=row.subject,
            phone=row.phone,
            category=row.category,
            message=row.message,
            attachments=_parse_json_list(row.attachments_json),
            status=row.status,
            source=row.source,
            user_id=str(row.user_id) if row.user_id else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return SupportRequestListResponse(items=items, total=total, skip=skip, limit=limit)


@router.patch("/requests/{request_id}/status", response_model=SupportStatusUpdateResponse)
async def update_support_request_status(
    request_id: UUID,
    payload: SupportStatusUpdateRequest,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> SupportStatusUpdateResponse:
    """Admin update status for a support request."""
    row = await session.get(SupportRequest, request_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada.",
        )

    row.status = payload.status
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return SupportStatusUpdateResponse(
        success=True,
        message="Estado actualizado correctamente.",
        item=SupportRequestListItem(
            id=str(row.id),
            name=row.name,
            email=row.email,
            subject=row.subject,
            phone=row.phone,
            category=row.category,
            message=row.message,
            attachments=_parse_json_list(row.attachments_json),
            status=row.status,
            source=row.source,
            user_id=str(row.user_id) if row.user_id else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        ),
    )


def _parse_json_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
    except Exception:
        return []
    return []


def _count_attachment_types(attachments: list[str]) -> tuple[int, int]:
    image_ext = {".jpg", ".jpeg", ".png"}
    document_ext = {".pdf", ".doc", ".docx"}
    image_count = 0
    document_count = 0
    for path in attachments:
        lower = path.lower()
        ext = ""
        if "." in lower:
            ext = "." + lower.rsplit(".", 1)[-1]
        if ext in image_ext:
            image_count += 1
        elif ext in document_ext:
            document_count += 1
    return image_count, document_count
