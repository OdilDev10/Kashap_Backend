"""Customer portal endpoints - /me/* for customers viewing their own loans and payments."""

from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.lender import Lender
from app.models.customer_lender_link import CustomerLenderLink
from app.core.enums import LenderStatus, LinkStatus
from app.repositories.customer_repo import CustomerRepository
from app.repositories.loan_repo import LoanRepository, InstallmentRepository
from app.repositories.payment_repo import PaymentRepository, VoucherRepository
from app.services.payment_service import PaymentService
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)


router = APIRouter(prefix="/me", tags=["customer-portal"])


class SubmitPaymentRequest(BaseModel):
    """Submit payment request for customer portal."""

    loan_id: str = Field(..., description="Loan ID")
    installment_id: str = Field(..., description="Installment ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")


class AssociationRequest(BaseModel):
    """Payload for requesting customer association to a lender."""

    lender_id: UUID = Field(..., description="Lender ID to associate with")


async def _ensure_legacy_link(customer: Customer, session: AsyncSession) -> None:
    """Backfill link table from legacy customer.lender_id when needed."""
    if not customer.lender_id:
        return

    existing = await session.execute(
        select(CustomerLenderLink).where(
            CustomerLenderLink.customer_id == customer.id,
            CustomerLenderLink.lender_id == customer.lender_id,
            CustomerLenderLink.status == LinkStatus.LINKED,
        )
    )
    if existing.scalar_one_or_none():
        return

    session.add(
        CustomerLenderLink(
            customer_id=customer.id,
            lender_id=customer.lender_id,
            status=LinkStatus.LINKED,
        )
    )
    await session.commit()


async def get_current_customer(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Customer:
    """Get the Customer profile for the authenticated user."""
    repo = CustomerRepository(session)

    # Customer portal is only valid for customer users.
    role_value = getattr(current_user.role, "value", current_user.role)
    if role_value != "customer":
        raise ForbiddenException("Customer account required")

    customer = await repo.get_by_user_id(current_user.id)
    if customer:
        return customer

    # Backward compatibility: old customer records may exist without user_id link.
    customer = await repo.get_by_email_and_lender(current_user.email, current_user.lender_id)
    if not customer:
        raise NotFoundException("No customer profile found for this user")

    if customer.user_id is None:
        await repo.update(customer, {"user_id": current_user.id})
        await session.commit()

    return customer


@router.post("/payments")
async def submit_payment(
    request: SubmitPaymentRequest,
    current_user: User = Depends(get_current_user),
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Submit payment for installment (customer portal)."""
    loan_repo = LoanRepository(session)
    installment_repo = InstallmentRepository(session)

    loan = await loan_repo.get_or_404(request.loan_id)
    if loan.customer_id != customer.id:
        raise ForbiddenException("This loan does not belong to your account")

    installment = await installment_repo.get_or_404(request.installment_id)
    if str(installment.loan_id) != request.loan_id:
        raise ValidationException("Installment does not belong to the specified loan")

    service = PaymentService(session)
    try:
        result = await service.submit_payment(
            loan_id=request.loan_id,
            installment_id=request.installment_id,
            customer_id=str(customer.id),
            lender_id=str(loan.lender_id),
            amount=request.amount,
            submitted_by_user_id=str(current_user.id),
            source="customer_portal",
        )
        return result
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/loans")
async def get_my_loans(
    lender_id: UUID | None = Query(default=None),
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get all loans for the authenticated customer."""
    loan_repo = LoanRepository(session)
    installment_repo = InstallmentRepository(session)

    if lender_id:
        link_result = await session.execute(
            select(CustomerLenderLink).where(
                CustomerLenderLink.customer_id == customer.id,
                CustomerLenderLink.lender_id == lender_id,
                CustomerLenderLink.status == LinkStatus.LINKED,
            )
        )
        if link_result.scalar_one_or_none() is None:
            raise ForbiddenException("No tienes asociación activa con esta financiera")
        loans = await loan_repo.get_by_customer_and_lender(str(customer.id), str(lender_id))
    else:
        loans = await loan_repo.get_by_customer(str(customer.id))

    items = []
    for loan in loans:
        installments = await installment_repo.get_by_loan(str(loan.id))
        balance = loan.total_amount - sum(inst.amount_paid for inst in installments)

        items.append(
            {
                "loan_id": str(loan.id),
                "loan_number": loan.loan_number,
                "principal": float(loan.principal_amount),
                "total_amount": float(loan.total_amount),
                "balance": float(balance),
                "interest_rate": float(loan.interest_rate),
                "status": loan.status.value,
                "installments_count": loan.installments_count,
                "frequency": loan.frequency,
                "first_due_date": loan.first_due_date.isoformat()
                if loan.first_due_date
                else None,
                "disbursement_date": loan.disbursement_date.isoformat()
                if loan.disbursement_date
                else None,
                "installments": [
                    {
                        "installment_id": str(inst.id),
                        "number": inst.installment_number,
                        "due_date": inst.due_date.isoformat(),
                        "amount": float(inst.amount_due),
                        "paid": float(inst.amount_paid),
                        "status": inst.status.value,
                    }
                    for inst in installments
                ],
                "created_at": loan.created_at.isoformat(),
            }
        )

    return {
        "count": len(items),
        "loans": items,
    }


@router.get("/association")
async def get_my_association(
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get customer-to-lender association details."""
    await _ensure_legacy_link(customer, session)
    link_result = await session.execute(
        select(CustomerLenderLink)
        .where(
            CustomerLenderLink.customer_id == customer.id,
            CustomerLenderLink.status == LinkStatus.LINKED,
        )
        .order_by(CustomerLenderLink.created_at.asc())
    )
    link = link_result.scalars().first()
    lender = None
    if link:
        lender_result = await session.execute(select(Lender).where(Lender.id == link.lender_id))
        lender = lender_result.scalar_one_or_none()

    return {
        "customer_id": str(customer.id),
        "lender_id": str(link.lender_id) if link else None,
        "lender_legal_name": lender.legal_name if lender else None,
        "lender_commercial_name": lender.commercial_name if lender else None,
        "lender_status": (
            lender.status.value
            if lender and hasattr(lender.status, "value")
            else (str(lender.status) if lender else None)
        ),
    }


@router.get("/associations")
async def list_my_associations(
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List all lenders currently associated to the authenticated customer."""
    await _ensure_legacy_link(customer, session)

    result = await session.execute(
        select(CustomerLenderLink, Lender)
        .join(Lender, Lender.id == CustomerLenderLink.lender_id)
        .where(
            CustomerLenderLink.customer_id == customer.id,
            CustomerLenderLink.status == LinkStatus.LINKED,
        )
        .order_by(CustomerLenderLink.created_at.desc())
    )
    rows = result.all()

    items = [
        {
            "lender_id": str(lender.id),
            "lender_legal_name": lender.legal_name,
            "lender_commercial_name": lender.commercial_name,
            "lender_status": (
                lender.status.value if hasattr(lender.status, "value") else str(lender.status)
            ),
        }
        for _, lender in rows
    ]

    return {"items": items, "total": len(items), "skip": 0, "limit": 20}


@router.get("/lenders")
async def list_lenders_for_customer(
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List active lenders available for customer association."""
    await _ensure_legacy_link(customer, session)

    links_result = await session.execute(
        select(CustomerLenderLink.lender_id).where(
            CustomerLenderLink.customer_id == customer.id,
            CustomerLenderLink.status == LinkStatus.LINKED,
        )
    )
    associated_lender_ids = {str(link_id) for link_id in links_result.scalars().all()}

    query = select(Lender).where(Lender.status == LenderStatus.ACTIVE)
    count_query = select(func.count(Lender.id)).where(Lender.status == LenderStatus.ACTIVE)

    if search:
        search_filter = or_(
            Lender.legal_name.ilike(f"%{search}%"),
            Lender.commercial_name.ilike(f"%{search}%"),
            Lender.document_number.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(
        query.order_by(Lender.created_at.desc()).offset(skip).limit(limit)
    )
    lenders = result.scalars().all()

    items = []
    for lender in lenders:
        items.append(
            {
                "id": str(lender.id),
                "legal_name": lender.legal_name,
                "commercial_name": lender.commercial_name,
                "lender_type": (
                    lender.lender_type.value
                    if hasattr(lender.lender_type, "value")
                    else str(lender.lender_type)
                ),
                "status": (
                    lender.status.value
                    if hasattr(lender.status, "value")
                    else str(lender.status)
                ),
                "is_associated": str(lender.id) in associated_lender_ids,
            }
        )

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/association/request")
async def request_association(
    request: AssociationRequest,
    current_user: User = Depends(get_current_user),
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Request (and apply) association for the current customer to a lender."""
    await _ensure_legacy_link(customer, session)

    lender_result = await session.execute(
        select(Lender).where(
            Lender.id == request.lender_id,
            Lender.status == LenderStatus.ACTIVE,
        )
    )
    lender = lender_result.scalar_one_or_none()
    if lender is None:
        raise NotFoundException("Lender no encontrado o no disponible")

    existing_link_result = await session.execute(
        select(CustomerLenderLink).where(
            CustomerLenderLink.customer_id == customer.id,
            CustomerLenderLink.lender_id == lender.id,
            CustomerLenderLink.status == LinkStatus.LINKED,
        )
    )
    if existing_link_result.scalar_one_or_none():
        return {
            "message": "Ya estás asociado a esta financiera",
            "lender_id": str(lender.id),
            "status": "already_linked",
        }

    session.add(
        CustomerLenderLink(
            customer_id=customer.id,
            lender_id=lender.id,
            status=LinkStatus.LINKED,
        )
    )

    # Legacy compatibility: keep a default lender on user/customer.
    if not customer.lender_id:
        customer.lender_id = lender.id
    if current_user.lender_id is None:
        current_user.lender_id = lender.id
    await session.commit()

    return {
        "message": "Solicitud de asociación completada",
        "lender_id": str(lender.id),
        "status": "linked",
    }


@router.get("/loans/{loan_id}")
async def get_my_loan_detail(
    loan_id: UUID,
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get loan details for the authenticated customer."""
    loan_repo = LoanRepository(session)
    installment_repo = InstallmentRepository(session)

    loan = await loan_repo.get_or_404(str(loan_id))

    if loan.customer_id != customer.id:
        raise ForbiddenException("You do not have permission to view this loan")

    installments = await installment_repo.get_by_loan(str(loan.id))
    balance = loan.total_amount - sum(inst.amount_paid for inst in installments)

    return {
        "loan_id": str(loan.id),
        "loan_number": loan.loan_number,
        "principal": float(loan.principal_amount),
        "total_amount": float(loan.total_amount),
        "total_interest": float(loan.total_interest_amount),
        "balance": float(balance),
        "interest_rate": float(loan.interest_rate),
        "status": loan.status.value,
        "frequency": loan.frequency,
        "first_due_date": loan.first_due_date.isoformat()
        if loan.first_due_date
        else None,
        "disbursement_date": loan.disbursement_date.isoformat()
        if loan.disbursement_date
        else None,
        "installments": [
            {
                "installment_id": str(inst.id),
                "number": inst.installment_number,
                "due_date": inst.due_date.isoformat(),
                "principal_component": float(inst.principal_component),
                "interest_component": float(inst.interest_component),
                "amount_due": float(inst.amount_due),
                "amount_paid": float(inst.amount_paid),
                "late_fee": float(inst.late_fee_amount),
                "status": inst.status.value,
                "paid_at": inst.paid_at.isoformat() if inst.paid_at else None,
            }
            for inst in installments
        ],
        "created_at": loan.created_at.isoformat(),
    }


@router.get("/payments")
async def get_my_payments(
    lender_id: UUID | None = Query(default=None),
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get all payments for the authenticated customer."""
    payment_repo = PaymentRepository(session)
    voucher_repo = VoucherRepository(session)

    payments = await payment_repo.get_by_customer(str(customer.id))
    if lender_id:
        link_result = await session.execute(
            select(CustomerLenderLink).where(
                CustomerLenderLink.customer_id == customer.id,
                CustomerLenderLink.lender_id == lender_id,
                CustomerLenderLink.status == LinkStatus.LINKED,
            )
        )
        if link_result.scalar_one_or_none() is None:
            raise ForbiddenException("No tienes asociación activa con esta financiera")
        payments = [payment for payment in payments if payment.lender_id == lender_id]

    items = []
    for payment in payments:
        vouchers = await voucher_repo.get_by_payment(str(payment.id))

        items.append(
            {
                "payment_id": str(payment.id),
                "loan_id": str(payment.loan_id),
                "installment_id": str(payment.installment_id)
                if payment.installment_id
                else None,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status.value,
                "submitted_at": payment.created_at.isoformat(),
                "reviewed_at": payment.reviewed_at.isoformat()
                if payment.reviewed_at
                else None,
                "review_notes": payment.review_notes,
                "vouchers_count": len(vouchers),
            }
        )

    return {
        "count": len(items),
        "payments": items,
    }


@router.get("/payments/{payment_id}")
async def get_my_payment_detail(
    payment_id: UUID,
    customer: Customer = Depends(get_current_customer),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get payment details for the authenticated customer."""
    payment_repo = PaymentRepository(session)
    voucher_repo = VoucherRepository(session)

    payment = await payment_repo.get_or_404(str(payment_id))

    if payment.customer_id != customer.id:
        raise ForbiddenException("You do not have permission to view this payment")

    vouchers = await voucher_repo.get_by_payment(str(payment.id))

    voucher_data = []
    for voucher in vouchers:
        voucher_data.append(
            {
                "voucher_id": str(voucher.id),
                "file_url": voucher.original_file_url,
                "status": voucher.status.value,
                "uploaded_at": voucher.created_at.isoformat(),
            }
        )

    return {
        "payment_id": str(payment.id),
        "loan_id": str(payment.loan_id),
        "installment_id": str(payment.installment_id)
        if payment.installment_id
        else None,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "status": payment.status.value,
        "method": payment.method.value,
        "submitted_at": payment.created_at.isoformat(),
        "reviewed_at": payment.reviewed_at.isoformat() if payment.reviewed_at else None,
        "review_notes": payment.review_notes,
        "vouchers": voucher_data,
    }
