"""Lender dashboard API - dashboard stats, loans, customers, payments, users."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from datetime import date
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from app.db.session import get_db
from app.dependencies import get_lender_context, require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.lender import LenderInvitation
from app.models.loan import Loan, LoanStatus
from app.models.payment import Payment, PaymentStatus
from app.models.customer_lender_link import CustomerLenderLink
from app.models.customer_document import CustomerDocument
from app.core.enums import LinkStatus
from app.schemas.dashboard import (
    LenderDashboardResponse,
    PaginatedLoansResponse,
    PaginatedCustomersResponse,
    PaginatedPaymentsResponse,
    PaginatedUsersResponse,
    LoanKPIs,
    PaymentKPIs,
)
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from app.services.storage_service import storage_service
from app.core.association_code import create_association_code
from app.services.email_service import email_service


router = APIRouter(prefix="/lender", tags=["lender"])


@router.get("/dashboard", response_model=LenderDashboardResponse)
async def get_lender_dashboard(
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> LenderDashboardResponse:
    """Get full dashboard with KPIs, charts, and recent activity."""
    service = DashboardService(session)
    data = await service.get_lender_dashboard(lender_id)
    return LenderDashboardResponse(**data)


@router.get("/loans")
async def list_lender_loans(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedLoansResponse:
    """List loans for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_loans(lender_id, search, status, skip, limit)
    return PaginatedLoansResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/loans/kpis")
async def get_loan_kpis(
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> LoanKPIs:
    """Get loan screen KPIs."""
    service = DashboardService(session)
    data = await service.get_loan_kpis(lender_id)
    return LoanKPIs(**data)


@router.get("/customers")
async def list_lender_customers(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedCustomersResponse:
    """List customers for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_customers(lender_id, search, status, skip, limit)
    return PaginatedCustomersResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/payments")
async def list_lender_payments(
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedPaymentsResponse:
    """List pending payment vouchers for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_pending_vouchers(lender_id, search, skip, limit)
    return PaginatedPaymentsResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/payments/kpis")
async def get_payment_kpis(
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaymentKPIs:
    """Get payment screen KPIs."""
    service = DashboardService(session)
    data = await service.get_payment_kpis(lender_id)
    return PaymentKPIs(**data)


class ApprovePaymentRequest(BaseModel):
    review_notes: str | None = None


class RejectPaymentRequest(BaseModel):
    reason: str


class CreateInvitationRequest(BaseModel):
    expires_in_days: int = 30
    invitee_name: str = Field(..., min_length=2, max_length=255)
    invitee_email: EmailStr
    invitee_phone: str | None = Field(default=None, min_length=7, max_length=30)
    principal_amount: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(..., ge=0, le=100)
    installments_count: int = Field(..., ge=1, le=120)
    frequency: str = Field(..., min_length=3, max_length=20)
    first_due_date: date
    purpose: str | None = Field(default=None, max_length=500)


@router.get("/invitations")
async def list_lender_invitations(
    status_filter: str = Query(default="all"),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List invitations for this lender with optional status/search filters."""
    lender_uuid = UUID(lender_id)
    normalized_status = (status_filter or "all").strip().lower()
    valid_statuses = {"all", "active", "used", "revoked", "expired"}
    if normalized_status not in valid_statuses:
        normalized_status = "all"

    base_query = (
        select(LenderInvitation, Customer)
        .outerjoin(Customer, Customer.id == LenderInvitation.used_by_customer_id)
        .where(LenderInvitation.lender_id == lender_uuid)
    )
    count_query = select(func.count(LenderInvitation.id)).where(
        LenderInvitation.lender_id == lender_uuid
    )

    if normalized_status != "all":
        now = datetime.now(UTC)
        if normalized_status == "expired":
            expired_filter = or_(
                LenderInvitation.expires_at < now,
                LenderInvitation.status == "expired",
            )
            base_query = base_query.where(expired_filter)
            count_query = count_query.where(expired_filter)
        else:
            base_query = base_query.where(LenderInvitation.status == normalized_status)
            count_query = count_query.where(LenderInvitation.status == normalized_status)

    if search and search.strip():
        term = search.strip()
        search_filter = or_(
            LenderInvitation.code.ilike(f"%{term}%"),
            Customer.email.ilike(f"%{term}%"),
            Customer.first_name.ilike(f"%{term}%"),
            Customer.last_name.ilike(f"%{term}%"),
            LenderInvitation.invitee_name.ilike(f"%{term}%"),
            LenderInvitation.invitee_email.ilike(f"%{term}%"),
            LenderInvitation.invitee_phone.ilike(f"%{term}%"),
        )
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(
        base_query.order_by(desc(LenderInvitation.created_at)).offset(skip).limit(limit)
    )
    rows = result.all()

    now = datetime.now(UTC)
    items = []
    for invitation, customer in rows:
        effective_status = invitation.status
        if invitation.status == "active" and invitation.expires_at < now:
            effective_status = "expired"

        used_by_name = None
        if customer is not None:
            used_by_name = f"{customer.first_name} {customer.last_name}".strip()

        items.append(
            {
                "id": str(invitation.id),
                "code": invitation.code,
                "status": effective_status,
                "expires_at": invitation.expires_at.isoformat()
                if invitation.expires_at
                else None,
                "used_at": invitation.used_at.isoformat() if invitation.used_at else None,
                "used_by_customer_id": str(invitation.used_by_customer_id)
                if invitation.used_by_customer_id
                else None,
                "used_by_name": used_by_name,
                "used_by_email": customer.email if customer is not None else None,
                "created_at": invitation.created_at.isoformat()
                if invitation.created_at
                else None,
                "loan_principal_amount": float(invitation.loan_principal_amount)
                if invitation.loan_principal_amount is not None
                else None,
                "loan_interest_rate": float(invitation.loan_interest_rate)
                if invitation.loan_interest_rate is not None
                else None,
                "loan_installments_count": invitation.loan_installments_count,
                "loan_frequency": invitation.loan_frequency,
                "loan_first_due_date": invitation.loan_first_due_date.isoformat()
                if invitation.loan_first_due_date
                else None,
                "loan_purpose": invitation.loan_purpose,
                "invitee_name": invitation.invitee_name,
                "invitee_email": invitation.invitee_email,
                "invitee_phone": invitation.invitee_phone,
            }
        )

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/invitations")
async def create_lender_invitation(
    request: CreateInvitationRequest,
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a new invitation code for customer linking."""
    expires_in_days = max(1, min(request.expires_in_days, 30))
    frequency = request.frequency.strip().lower()
    if frequency not in {"weekly", "biweekly", "monthly"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Frecuencia inválida. Usa weekly, biweekly o monthly",
        )
    expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    invitation_code = secrets.token_urlsafe(18)[:24].upper()
    while True:
        code_exists_result = await session.execute(
            select(LenderInvitation.id)
            .where(LenderInvitation.code == invitation_code)
            .limit(1)
        )
        if code_exists_result.scalar_one_or_none() is None:
            break
        invitation_code = secrets.token_urlsafe(18)[:24].upper()

    invitation = LenderInvitation(
        lender_id=UUID(lender_id),
        code=invitation_code,
        expires_at=expires_at,
        created_by_user_id=current_user.id,
        status="active",
        invitee_name=request.invitee_name.strip(),
        invitee_email=str(request.invitee_email).strip().lower(),
        invitee_phone=request.invitee_phone.strip() if request.invitee_phone else None,
        loan_principal_amount=request.principal_amount,
        loan_interest_rate=request.interest_rate,
        loan_installments_count=request.installments_count,
        loan_frequency=frequency,
        loan_first_due_date=request.first_due_date,
        loan_purpose=request.purpose,
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)

    existing_customer_result = await session.execute(
        select(Customer.id)
        .where(Customer.email == invitation.invitee_email)
        .limit(1)
    )
    invitee_registered = existing_customer_result.scalar_one_or_none() is not None

    email_sent: bool | None = None
    if invitation.invitee_email:
        subject = "Invitación de vinculación y préstamo - OptiCredit"
        register_hint = (
            "Solo debes iniciar sesión en tu cuenta y colocar el código."
            if invitee_registered
            else "Si aún no tienes cuenta, primero regístrate en la plataforma y luego coloca este código."
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.5;">
          <h2>Hola {invitation.invitee_name or "cliente"},</h2>
          <p>Tu prestamista te ha enviado una invitación de vinculación con un préstamo preacordado.</p>
          <p><strong>Código de vinculación:</strong> {invitation.code}</p>
          <p><strong>Vigencia:</strong> {invitation.expires_at.strftime("%Y-%m-%d %H:%M UTC")}</p>
          <hr />
          <p><strong>Monto:</strong> RD$ {float(invitation.loan_principal_amount or 0):,.2f}</p>
          <p><strong>Interés:</strong> {float(invitation.loan_interest_rate or 0):.2f}%</p>
          <p><strong>Cuotas:</strong> {invitation.loan_installments_count or 0}</p>
          <p><strong>Frecuencia:</strong> {invitation.loan_frequency or "N/A"}</p>
          <p><strong>Primer vencimiento:</strong> {invitation.loan_first_due_date.isoformat() if invitation.loan_first_due_date else "N/A"}</p>
          <p><strong>Propósito:</strong> {invitation.loan_purpose or "N/A"}</p>
          <hr />
          <p>{register_hint}</p>
          <p>Ingresa este código en tu panel de cliente para completar la vinculación.</p>
        </div>
        """
        email_sent = await email_service.send_email(
            to_email=invitation.invitee_email,
            subject=subject,
            body=html,
            is_html=True,
        )

    return {
        "id": str(invitation.id),
        "code": invitation.code,
        "status": invitation.status,
        "expires_at": invitation.expires_at.isoformat(),
        "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
        "loan_principal_amount": float(invitation.loan_principal_amount)
        if invitation.loan_principal_amount is not None
        else None,
        "loan_interest_rate": float(invitation.loan_interest_rate)
        if invitation.loan_interest_rate is not None
        else None,
        "loan_installments_count": invitation.loan_installments_count,
        "loan_frequency": invitation.loan_frequency,
        "loan_first_due_date": invitation.loan_first_due_date.isoformat()
        if invitation.loan_first_due_date
        else None,
        "loan_purpose": invitation.loan_purpose,
        "invitee_name": invitation.invitee_name,
        "invitee_email": invitation.invitee_email,
        "invitee_phone": invitation.invitee_phone,
        "invitee_registered": invitee_registered,
        "email_sent": email_sent,
        "message": "Invitacion creada",
    }


@router.post("/invitations/{invitation_id}/cancel")
async def cancel_lender_invitation(
    invitation_id: UUID,
    _current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel an active invitation code."""
    result = await session.execute(
        select(LenderInvitation)
        .where(
            LenderInvitation.id == invitation_id,
            LenderInvitation.lender_id == UUID(lender_id),
        )
        .limit(1)
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        return {"success": False, "message": "Invitacion no encontrada"}

    if invitation.status != "active":
        return {
            "success": False,
            "message": "Solo puedes cancelar invitaciones activas",
            "status": invitation.status,
        }

    invitation.status = "revoked"
    await session.commit()
    return {
        "success": True,
        "id": str(invitation.id),
        "status": invitation.status,
        "message": "Invitacion cancelada",
    }


@router.post("/association-code")
async def generate_association_code(
    expires_minutes: int = Query(default=30, ge=5, le=120),
    _current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
) -> dict:
    """Generate a short-lived code to link a customer with this lender."""
    try:
        code = create_association_code(lender_id=lender_id, expires_minutes=expires_minutes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el código de vinculación",
        ) from exc

    return {
        "code": code,
        "expires_minutes": expires_minutes,
        "message": "Código generado exitosamente",
    }


@router.post("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: UUID,
    request: ApprovePaymentRequest | None = None,
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a payment voucher."""
    service = PaymentService(session)
    await service.approve_payment(
        str(payment_id),
        lender_id,
        str(current_user.id),
        request.review_notes if request else None,
    )
    return {"success": True, "message": "Payment approved"}


@router.post("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: UUID,
    request: RejectPaymentRequest,
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a payment voucher with reason."""
    service = PaymentService(session)
    await service.reject_payment(
        str(payment_id), lender_id, str(current_user.id), request.reason
    )
    return {"success": True, "message": "Payment rejected"}


@router.get("/customers/{customer_id}/loans")
async def get_customer_loans_for_lender(
    customer_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get loans for a specific customer in lender scope."""
    service = DashboardService(session)
    items = await service.get_customer_loans(lender_id, str(customer_id), limit)
    return {"items": items, "total": len(items), "limit": limit}


@router.get("/customers/{customer_id}/payments")
async def get_customer_payments_for_lender(
    customer_id: UUID,
    limit: int = Query(default=200, ge=1, le=500),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get payment history for a specific customer in lender scope."""
    service = DashboardService(session)
    items = await service.get_customer_payment_history(
        lender_id, str(customer_id), limit
    )
    return {"items": items, "total": len(items), "limit": limit}


@router.get("/users")
async def list_lender_users(
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedUsersResponse:
    """List users for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_users(lender_id, search, skip, limit)
    return PaginatedUsersResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/association-requests")
async def list_association_requests(
    status_filter: str = Query(default="pending"),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List customer association requests for this lender."""
    normalized_status = (status_filter or "pending").strip().lower()
    if normalized_status not in {"pending", "linked", "unlinked", "all"}:
        normalized_status = "pending"

    base_query = (
        select(CustomerLenderLink, Customer)
        .join(Customer, Customer.id == CustomerLenderLink.customer_id)
        .where(CustomerLenderLink.lender_id == lender_id)
    )
    count_query = select(func.count(CustomerLenderLink.id)).where(
        CustomerLenderLink.lender_id == lender_id
    )

    if normalized_status != "all":
        status_enum = LinkStatus(normalized_status)
        base_query = base_query.where(CustomerLenderLink.status == status_enum)
        count_query = count_query.where(CustomerLenderLink.status == status_enum)

    if search:
        search_term = search.strip()
        if search_term:
            search_filter = or_(
                Customer.first_name.ilike(f"%{search_term}%"),
                Customer.last_name.ilike(f"%{search_term}%"),
                Customer.email.ilike(f"%{search_term}%"),
                Customer.document_number.ilike(f"%{search_term}%"),
            )
            base_query = base_query.where(search_filter)
            count_query = count_query.where(search_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(
        base_query.order_by(desc(CustomerLenderLink.created_at))
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()

    items = []
    for link, customer in rows:
        items.append(
            {
                "request_id": str(link.id),
                "customer_id": str(customer.id),
                "full_name": f"{customer.first_name} {customer.last_name}",
                "email": customer.email,
                "phone": customer.phone,
                "document_type": customer.document_type,
                "document_number": customer.document_number,
                "status": link.status.value,
                "requested_at": link.created_at.isoformat()
                if link.created_at
                else None,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None,
            }
        )

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/association-requests/{request_id}/approve")
async def approve_association_request(
    request_id: UUID,
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a pending customer association request."""
    result = await session.execute(
        select(CustomerLenderLink)
        .where(
            CustomerLenderLink.id == request_id,
            CustomerLenderLink.lender_id == lender_id,
        )
        .limit(1)
    )
    link = result.scalar_one_or_none()
    if link is None:
        return {"success": False, "message": "Solicitud no encontrada"}

    link.status = LinkStatus.LINKED

    customer_result = await session.execute(
        select(Customer).where(Customer.id == link.customer_id).limit(1)
    )
    customer = customer_result.scalar_one_or_none()
    if customer and customer.lender_id is None:
        customer.lender_id = UUID(lender_id)

    await session.commit()
    return {
        "success": True,
        "request_id": str(link.id),
        "status": link.status.value,
        "message": "Solicitud aprobada",
    }


@router.post("/association-requests/{request_id}/reject")
async def reject_association_request(
    request_id: UUID,
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a pending customer association request."""
    result = await session.execute(
        select(CustomerLenderLink)
        .where(
            CustomerLenderLink.id == request_id,
            CustomerLenderLink.lender_id == lender_id,
        )
        .limit(1)
    )
    link = result.scalar_one_or_none()
    if link is None:
        return {"success": False, "message": "Solicitud no encontrada"}

    link.status = LinkStatus.UNLINKED
    await session.commit()
    return {
        "success": True,
        "request_id": str(link.id),
        "status": link.status.value,
        "message": "Solicitud rechazada",
    }


@router.get("/customers/{customer_id}/profile")
async def get_customer_profile_for_lender(
    customer_id: UUID,
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return rich customer profile for lender detail view."""
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id).limit(1)
    )
    customer = customer_result.scalar_one_or_none()
    if customer is None:
        return {"success": False, "message": "Cliente no encontrado"}

    # Tenant guard: customer belongs to this lender OR has an association link to this lender.
    link_result = await session.execute(
        select(CustomerLenderLink)
        .where(
            CustomerLenderLink.customer_id == customer.id,
            CustomerLenderLink.lender_id == lender_id,
        )
        .limit(1)
    )
    link = link_result.scalar_one_or_none()
    if str(customer.lender_id) != str(lender_id) and link is None:
        return {"success": False, "message": "Cliente fuera de tu cartera"}

    loans_result = await session.execute(
        select(Loan)
        .where(Loan.customer_id == customer.id, Loan.lender_id == lender_id)
        .order_by(desc(Loan.created_at))
    )
    loans = loans_result.scalars().all()

    payments_result = await session.execute(
        select(Payment)
        .where(Payment.customer_id == customer.id, Payment.lender_id == lender_id)
        .order_by(desc(Payment.created_at))
    )
    payments = payments_result.scalars().all()

    documents_result = await session.execute(
        select(CustomerDocument)
        .where(CustomerDocument.customer_id == customer.id)
        .order_by(desc(CustomerDocument.created_at))
    )
    documents = documents_result.scalars().all()

    approved_count = sum(1 for p in payments if p.status == PaymentStatus.APPROVED)
    rejected_count = sum(1 for p in payments if p.status == PaymentStatus.REJECTED)
    under_review_count = sum(
        1
        for p in payments
        if p.status in {PaymentStatus.SUBMITTED, PaymentStatus.UNDER_REVIEW}
    )
    approved_amount = float(
        sum((p.amount for p in payments if p.status == PaymentStatus.APPROVED), start=0)
    )
    active_loan_count = sum(
        1 for loan in loans if loan.status in {LoanStatus.ACTIVE, LoanStatus.OVERDUE}
    )

    loan_history = [
        {
            "loan_id": str(loan.id),
            "loan_number": loan.loan_number,
            "principal_amount": float(loan.principal_amount),
            "total_amount": float(loan.total_amount),
            "status": loan.status.value,
            "created_at": loan.created_at.isoformat() if loan.created_at else None,
        }
        for loan in loans
    ]

    document_items = []
    for doc in documents:
        file_url = None
        try:
            file_url = await storage_service.generate_url(doc.file_path)
        except Exception:
            file_url = None
        document_items.append(
            {
                "id": str(doc.id),
                "document_type": doc.document_type.value
                if hasattr(doc.document_type, "value")
                else str(doc.document_type),
                "status": doc.status,
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "file_url": file_url,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "reviewed_at": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
                "notes": doc.notes,
            }
        )

    return {
        "success": True,
        "customer": {
            "id": str(customer.id),
            "full_name": f"{customer.first_name} {customer.last_name}",
            "email": customer.email,
            "phone": customer.phone,
            "document_type": customer.document_type,
            "document_number": customer.document_number,
            "status": customer.status.value
            if hasattr(customer.status, "value")
            else str(customer.status),
            "created_at": customer.created_at.isoformat()
            if customer.created_at
            else None,
            "association_status": link.status.value if link else "linked",
        },
        "credit_history": {
            "loan_count": len(loans),
            "active_loan_count": active_loan_count,
            "approved_payments_count": approved_count,
            "under_review_payments_count": under_review_count,
            "rejected_payments_count": rejected_count,
            "approved_payments_amount": approved_amount,
        },
        "loan_history": loan_history,
        "documents": document_items,
    }
