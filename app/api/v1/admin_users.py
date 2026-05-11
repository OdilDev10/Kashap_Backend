"""Admin Users API - Platform user management with pagination and review."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.models.lender import Lender
from app.models.customer import Customer
from app.models.customer_document import CustomerDocument
from app.models.lender_document import LenderDocument
from app.repositories.user_repo import UserRepository
from app.core.enums import UserStatus
from app.services.storage_service import storage_service


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class UserVerificationRequest(BaseModel):
    verified: bool
    notes: str | None = Field(default=None, max_length=500)


class UserDocumentReviewRequest(BaseModel):
    source: str = Field(..., pattern="^(customer|lender)$")
    status: str = Field(..., pattern="^(validated|rejected)$")
    notes: str | None = Field(default=None, max_length=500)


def _serialize_user_card(user: User, lender_name: str | None) -> dict:
    """Serialize user row for admin responses."""
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "account_type": user.account_type.value
        if hasattr(user.account_type, "value")
        else str(user.account_type),
        "status": user.status.value if hasattr(user.status, "value") else str(user.status),
        "lender_id": str(user.lender_id) if user.lender_id else None,
        "lender_name": lender_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        # Optional audit fields (may not exist in current schema yet).
        "disabled_at": (
            user.disabled_at.isoformat()
            if getattr(user, "disabled_at", None)
            else None
        ),
        "disabled_by": (
            str(getattr(user, "disabled_by")) if getattr(user, "disabled_by", None) else None
        ),
        "enabled_at": (
            user.enabled_at.isoformat()
            if getattr(user, "enabled_at", None)
            else None
        ),
        "enabled_by": (
            str(getattr(user, "enabled_by")) if getattr(user, "enabled_by", None) else None
        ),
        "is_verified": bool(getattr(user, "is_verified", False)),
        "verified_at": (
            user.verified_at.isoformat()
            if getattr(user, "verified_at", None)
            else None
        ),
        "verification_notes": getattr(user, "verification_notes", None),
    }


async def _safe_file_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    try:
        return await storage_service.generate_url(file_path, expires_in=3600)
    except Exception:
        return None


@router.get("")
async def list_admin_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List all users for admin with pagination and search."""
    repo = UserRepository(session)
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if status:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
    result = await session.execute(query)
    users = result.scalars().all()

    items = []
    for user in users:
        lender_name = None
        if user.lender_id:
            lender_result = await session.execute(
                select(Lender.legal_name).where(Lender.id == str(user.lender_id))
            )
            lender_name = lender_result.scalar_one_or_none()

        items.append(_serialize_user_card(user, lender_name))

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{user_id}/detail")
async def get_admin_user_detail(
    user_id: str,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get full user detail, linked lender/customer, and documents for verification."""
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    lender_name = None
    lender_payload: dict | None = None
    lender_documents: list[dict] = []
    if user.lender_id:
        lender_result = await session.execute(select(Lender).where(Lender.id == user.lender_id))
        lender = lender_result.scalar_one_or_none()
        if lender:
            lender_name = lender.legal_name
            lender_payload = {
                "id": str(lender.id),
                "legal_name": lender.legal_name,
                "commercial_name": lender.commercial_name,
                "email": lender.email,
                "phone": lender.phone,
                "document_type": lender.document_type,
                "document_number": lender.document_number,
                "status": lender.status.value if hasattr(lender.status, "value") else str(lender.status),
                "is_verified": bool(getattr(lender, "is_verified", False)),
                "verification_notes": getattr(lender, "verification_notes", None),
            }
            lender_docs_result = await session.execute(
                select(LenderDocument)
                .where(LenderDocument.lender_id == lender.id)
                .order_by(LenderDocument.created_at.desc())
            )
            for doc in lender_docs_result.scalars().all():
                lender_documents.append(
                    {
                        "id": str(doc.id),
                        "source": "lender",
                        "document_type": doc.document_type,
                        "file_name": doc.file_name,
                        "status": doc.status,
                        "notes": doc.notes,
                        "file_url": await _safe_file_url(doc.file_path),
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                )

    customer_payload: dict | None = None
    customer_documents: list[dict] = []
    customer_result = await session.execute(select(Customer).where(Customer.user_id == user.id))
    customer = customer_result.scalar_one_or_none()
    if customer:
        customer_payload = {
            "id": str(customer.id),
            "full_name": f"{customer.first_name} {customer.last_name}",
            "email": customer.email,
            "phone": customer.phone,
            "document_type": customer.document_type,
            "document_number": customer.document_number,
            "status": customer.status.value if hasattr(customer.status, "value") else str(customer.status),
            "is_verified": bool(getattr(customer, "is_verified", False)),
            "verification_notes": getattr(customer, "verification_notes", None),
        }
        customer_docs_result = await session.execute(
            select(CustomerDocument)
            .where(CustomerDocument.customer_id == customer.id)
            .order_by(CustomerDocument.created_at.desc())
        )
        for doc in customer_docs_result.scalars().all():
            doc_type = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
            customer_documents.append(
                {
                    "id": str(doc.id),
                    "source": "customer",
                    "document_type": doc_type,
                    "file_name": doc.file_name,
                    "status": doc.status,
                    "notes": doc.notes,
                    "file_url": await _safe_file_url(doc.file_path),
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
            )

    return {
        "user": _serialize_user_card(user, lender_name),
        "lender": lender_payload,
        "customer": customer_payload,
        "documents": [*customer_documents, *lender_documents],
    }


@router.patch("/{user_id}/verification", status_code=status.HTTP_200_OK)
async def set_user_verification(
    user_id: str,
    payload: UserVerificationRequest,
    current_admin: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Verify/reject user and linked customer/lender profile."""
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    now = datetime.now(timezone.utc)
    user.is_verified = payload.verified
    user.verified_at = now
    user.verified_by = current_admin.id
    user.verification_notes = payload.notes

    customer_result = await session.execute(select(Customer).where(Customer.user_id == user.id))
    customer = customer_result.scalar_one_or_none()
    if customer:
        customer.is_verified = payload.verified
        customer.verified_at = now
        customer.verified_by = current_admin.id
        customer.verification_notes = payload.notes

    if user.lender_id:
        lender_result = await session.execute(select(Lender).where(Lender.id == user.lender_id))
        lender = lender_result.scalar_one_or_none()
        if lender:
            lender.is_verified = payload.verified
            lender.verified_at = now
            lender.verified_by = current_admin.id
            lender.verification_notes = payload.notes

    await session.commit()
    return {
        "success": True,
        "message": "Verificación actualizada",
        "user_id": str(user.id),
        "is_verified": user.is_verified,
    }


@router.patch("/{user_id}/documents/{document_id}/review", status_code=status.HTTP_200_OK)
async def review_user_document(
    user_id: str,
    document_id: str,
    payload: UserDocumentReviewRequest,
    current_admin: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Review customer or lender document from user detail modal."""
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.source == "customer":
        customer_result = await session.execute(select(Customer).where(Customer.user_id == user.id))
        customer = customer_result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer profile not found")
        doc_result = await session.execute(
            select(CustomerDocument).where(
                CustomerDocument.id == document_id,
                CustomerDocument.customer_id == customer.id,
            )
        )
        document = doc_result.scalar_one_or_none()
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        document.status = payload.status
        document.notes = payload.notes
        document.reviewed_by = current_admin.id
        document.reviewed_at = datetime.now(timezone.utc)
        await session.commit()
        return {"success": True, "message": "Documento de cliente revisado"}

    if not user.lender_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lender profile not found")
    doc_result = await session.execute(
        select(LenderDocument).where(
            LenderDocument.id == document_id,
            LenderDocument.lender_id == user.lender_id,
        )
    )
    lender_doc = doc_result.scalar_one_or_none()
    if lender_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    lender_doc.status = payload.status
    lender_doc.notes = payload.notes
    lender_doc.verified_by = current_admin.id
    lender_doc.verified_at = datetime.now(timezone.utc)
    await session.commit()
    return {"success": True, "message": "Documento de prestamista revisado"}


@router.get("/kpis")
async def get_admin_user_kpis(
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get admin dashboard KPIs for users."""
    total_result = await session.execute(select(func.count(User.id)))
    total = total_result.scalar() or 0

    active_result = await session.execute(
        select(func.count(User.id)).where(User.status == "active")
    )
    active = active_result.scalar() or 0

    inactive_result = await session.execute(
        select(func.count(User.id)).where(User.status == "inactive")
    )
    inactive = inactive_result.scalar() or 0

    blocked_result = await session.execute(
        select(func.count(User.id)).where(User.status == "blocked")
    )
    blocked = blocked_result.scalar() or 0

    platform_admins_result = await session.execute(
        select(func.count(User.id)).where(User.role == "platform_admin")
    )
    platform_admins = platform_admins_result.scalar() or 0

    return {
        "total_users": total,
        "active_users": active,
        "inactive_users": inactive,
        "platform_admins": platform_admins,
    }


@router.patch("/{user_id}/disable", status_code=status.HTTP_200_OK)
async def disable_user(
    user_id: str,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Disable a user account (set status to blocked)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = UserStatus.BLOCKED
    session.add(user)
    await session.commit()
    await session.refresh(user)

    lender_name = None
    if user.lender_id:
        lender_result = await session.execute(
            select(Lender.legal_name).where(Lender.id == str(user.lender_id))
        )
        lender_name = lender_result.scalar_one_or_none()

    return {
        "success": True,
        "message": "User disabled successfully",
        "user": _serialize_user_card(user, lender_name),
    }


@router.patch("/{user_id}/enable", status_code=status.HTTP_200_OK)
async def enable_user(
    user_id: str,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Enable a user account (set status to active)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = UserStatus.ACTIVE
    session.add(user)
    await session.commit()
    await session.refresh(user)

    lender_name = None
    if user.lender_id:
        lender_result = await session.execute(
            select(Lender.legal_name).where(Lender.id == str(user.lender_id))
        )
        lender_name = lender_result.scalar_one_or_none()

    return {
        "success": True,
        "message": "User enabled successfully",
        "user": _serialize_user_card(user, lender_name),
    }
