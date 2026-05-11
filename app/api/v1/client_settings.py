"""Client settings API - profile and account management."""

import asyncio
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.loan import Loan, Installment
from app.models.customer_document import CustomerDocument
from app.models.client_bank_account import ClientBankAccount
from app.core.enums import (
    CustomerStatus,
    DocumentType,
    UserStatus,
    LoanStatus,
    InstallmentStatus,
    OcrStatus,
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.storage_service import storage_service


router = APIRouter(prefix="/client/settings", tags=["client-settings"])


class ClientProfileResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    address_line: str | None = None
    status: str


class UpdateClientProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


@router.get("")
async def get_client_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ClientProfileResponse:
    """Get client profile information."""
    result = await session.execute(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        return ClientProfileResponse(
            id=str(current_user.id),
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            phone=current_user.phone,
            status="active",
        )

    return ClientProfileResponse(
        id=str(customer.id),
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        phone=customer.phone,
        document_type=customer.document_type,
        document_number=customer.document_number,
        address_line=customer.address_line,
        status=customer.status.value
        if hasattr(customer.status, "value")
        else customer.status,
    )


@router.put("")
async def update_client_profile(
    request: UpdateClientProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update client profile information."""
    result = await session.execute(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    customer = result.scalar_one_or_none()

    if customer:
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(customer, field, value)
        customer.updated_at = datetime.now(timezone.utc)
    else:
        if request.first_name:
            current_user.first_name = request.first_name
        if request.last_name:
            current_user.last_name = request.last_name
        if request.phone:
            current_user.phone = request.phone
        current_user.updated_at = datetime.now(timezone.utc)

    await session.commit()
    return {"success": True, "message": "Profile updated"}


@router.delete("/account")
async def delete_client_account(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Schedule client account deletion after business-rule checks."""
    result = await session.execute(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CUSTOMER_NOT_FOUND",
                "message": "Customer profile not found",
            },
        )

    unpaid_installments_query = (
        select(func.count(Installment.id))
        .select_from(Installment)
        .join(Loan, Loan.id == Installment.loan_id)
        .where(
            Loan.customer_id == customer.id,
            Loan.status.in_(
                [
                    LoanStatus.APPROVED,
                    LoanStatus.DISBURSED,
                    LoanStatus.ACTIVE,
                    LoanStatus.OVERDUE,
                ]
            ),
            Installment.status.in_(
                [
                    InstallmentStatus.PENDING,
                    InstallmentStatus.UNDER_REVIEW,
                    InstallmentStatus.PARTIAL,
                    InstallmentStatus.OVERDUE,
                    InstallmentStatus.REJECTED,
                ]
            ),
        )
    )
    unpaid_installments = await session.scalar(unpaid_installments_query)
    if unpaid_installments and unpaid_installments > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ACCOUNT_DELETION_BLOCKED_PENDING_DEBT",
                "message": "No puedes eliminar tu cuenta con deudas pendientes.",
                "detail": {
                    "pending_installments": int(unpaid_installments),
                },
            },
        )

    now = datetime.now(timezone.utc)
    scheduled_deletion_at = now + timedelta(days=30)

    customer.status = CustomerStatus.BLOCKED
    customer.updated_at = now
    current_user.status = UserStatus.INACTIVE
    current_user.updated_at = now

    await AuthService(session).logout_all(str(current_user.id))
    await AuditService(session).log(
        action="delete",
        resource_type="customer_account",
        resource_id=str(customer.id),
        description="Client account scheduled for deletion in 30 days",
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=f"{current_user.first_name} {current_user.last_name}",
        lender_id=customer.lender_id,
        metadata={
            "requested_at": now.isoformat(),
            "scheduled_deletion_at": scheduled_deletion_at.isoformat(),
            "retention_policy": "soft-delete-audit-retention",
        },
    )

    await session.commit()
    return {
        "success": True,
        "message": "Cuenta programada para eliminación en 30 días",
        "scheduled_deletion_at": scheduled_deletion_at.isoformat(),
        "retention_policy": "soft-delete-audit-retention",
    }


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"}


async def get_customer_or_404(
    current_user: User,
    session: AsyncSession,
) -> Customer:
    """Get customer profile or raise 404."""
    result = await session.execute(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return customer


class DocumentResponse(BaseModel):
    id: str
    document_type: str
    file_name: str
    file_size: int | None
    mime_type: str
    status: str
    bank_account_id: str | None
    created_at: str


@router.get("/documents")
async def list_client_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List all documents for the authenticated client."""
    customer = await get_customer_or_404(current_user, session)

    result = await session.execute(
        select(CustomerDocument)
        .where(CustomerDocument.customer_id == customer.id)
        .order_by(CustomerDocument.created_at.desc())
    )
    documents = result.scalars().all()

    return {
        "documents": [
            {
                "id": str(doc.id),
                "document_type": doc.document_type.value
                if hasattr(doc.document_type, "value")
                else doc.document_type,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "status": doc.status,
                "bank_account_id": str(doc.bank_account_id)
                if doc.bank_account_id
                else None,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in documents
        ]
    }


@router.post("/documents")
async def upload_client_document(
    document_type: DocumentType,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    bank_account_id: str | None = None,
) -> DocumentResponse:
    """Upload a document for the authenticated client (ID or financial document)."""
    customer = await get_customer_or_404(current_user, session)

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    ext = "." + file.filename.split(".")[-1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    bank_account_uuid = None
    if bank_account_id:
        try:
            bank_account_uuid = UUID(bank_account_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bank account ID")

    file_content = await file.read()
    file_size = len(file_content)

    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = await storage_service.upload(
        file_content,
        unique_name,
        folder="customer_documents",
    )

    document = CustomerDocument(
        customer_id=customer.id,
        document_type=document_type,
        file_name=file.filename or unique_name,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        status="pending",
        bank_account_id=bank_account_uuid,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    return DocumentResponse(
        id=str(document.id),
        document_type=document.document_type.value
        if hasattr(document.document_type, "value")
        else document.document_type,
        file_name=document.file_name,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status,
        bank_account_id=str(document.bank_account_id)
        if document.bank_account_id
        else None,
        created_at=document.created_at.isoformat(),
    )


@router.delete("/documents/{document_id}")
async def delete_client_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete a client document."""
    customer = await get_customer_or_404(current_user, session)

    result = await session.execute(
        select(CustomerDocument).where(
            CustomerDocument.id == document_id,
            CustomerDocument.customer_id == customer.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        await storage_service.delete(document.file_path)
    except Exception:
        pass

    await session.delete(document)
    await session.commit()

    return {"success": True, "message": "Document deleted"}


# === Bank Accounts ===


class BankAccountResponse(BaseModel):
    id: str
    bank_name: str
    account_type: str
    account_number_masked: str
    account_holder_name: str
    currency: str
    is_primary: bool
    status: str
    created_at: str


class CreateBankAccountRequest(BaseModel):
    bank_name: str
    account_type: str
    account_number: str
    account_holder_name: str
    currency: str = "DOP"
    is_primary: bool = False


def mask_account_number(number: str) -> str:
    """Mask all but last 4 digits."""
    if len(number) <= 4:
        return number
    return "*" * (len(number) - 4) + number[-4:]


@router.get("/accounts")
async def list_client_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List all bank accounts for the authenticated client."""
    customer = await get_customer_or_404(current_user, session)

    result = await session.execute(
        select(ClientBankAccount)
        .where(ClientBankAccount.customer_id == customer.id)
        .order_by(
            ClientBankAccount.is_primary.desc(), ClientBankAccount.created_at.desc()
        )
    )
    accounts = result.scalars().all()

    return {
        "accounts": [
            {
                "id": str(acc.id),
                "bank_name": acc.bank_name,
                "account_type": acc.account_type,
                "account_number_masked": acc.account_number_masked,
                "account_holder_name": acc.account_holder_name,
                "currency": acc.currency,
                "is_primary": acc.is_primary,
                "status": acc.status,
                "created_at": acc.created_at.isoformat(),
            }
            for acc in accounts
        ]
    }


@router.post("/accounts")
async def create_bank_account(
    request: CreateBankAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BankAccountResponse:
    """Create a new bank account for the authenticated client."""
    customer = await get_customer_or_404(current_user, session)

    existing_accounts_result = await session.execute(
        select(ClientBankAccount).where(
            ClientBankAccount.customer_id == customer.id,
            ClientBankAccount.status != "deleted",
        )
    )
    existing_accounts = existing_accounts_result.scalars().all()
    has_primary = any(acc.is_primary for acc in existing_accounts)

    should_be_primary = request.is_primary or not has_primary
    if should_be_primary:
        for acc in existing_accounts:
            if acc.is_primary:
                acc.is_primary = False

    account = ClientBankAccount(
        customer_id=customer.id,
        bank_name=request.bank_name,
        account_type=request.account_type,
        account_number_masked=mask_account_number(request.account_number),
        account_holder_name=request.account_holder_name,
        currency=request.currency,
        is_primary=should_be_primary,
        status="active",
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    return BankAccountResponse(
        id=str(account.id),
        bank_name=account.bank_name,
        account_type=account.account_type,
        account_number_masked=account.account_number_masked,
        account_holder_name=account.account_holder_name,
        currency=account.currency,
        is_primary=account.is_primary,
        status=account.status,
        created_at=account.created_at.isoformat(),
    )


@router.delete("/accounts/{account_id}")
async def delete_bank_account(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete a bank account (only if no pending disbursements)."""
    customer = await get_customer_or_404(current_user, session)

    result = await session.execute(
        select(ClientBankAccount).where(
            ClientBankAccount.id == account_id,
            ClientBankAccount.customer_id == customer.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.balance and account.balance > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete account with pending balance. Please transfer funds first.",
        )

    account.status = "deleted"
    account.updated_at = datetime.now(timezone.utc)
    await session.commit()

    return {"success": True, "message": "Account deleted"}


@router.put("/accounts/{account_id}/primary")
async def set_primary_account(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Set a bank account as primary."""
    customer = await get_customer_or_404(current_user, session)

    result = await session.execute(
        select(ClientBankAccount).where(
            ClientBankAccount.id == account_id,
            ClientBankAccount.customer_id == customer.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    result_all = await session.execute(
        select(ClientBankAccount).where(
            ClientBankAccount.customer_id == customer.id,
            ClientBankAccount.is_primary.is_(True),
        )
    )
    for acc in result_all.scalars().all():
        acc.is_primary = False

    account.is_primary = True
    account.updated_at = datetime.now(timezone.utc)
    await session.commit()

    return {"success": True, "message": "Primary account updated"}


class CedulaOcrRequest(BaseModel):
    document_side: str  # "front" or "back"
    document_id: str | None = None  # Optional existing customer_document ID


class CedulaOcrResponse(BaseModel):
    id: str
    document_side: str
    status: str
    confidence_score: float
    extracted_data: dict
    comparison_result: dict | None = None
    matches_customer_data: bool
    verification_notes: str | None = None


class CedulaDocumentResponse(BaseModel):
    id: str
    document_type: str
    file_name: str
    file_size: int | None
    mime_type: str
    status: str
    created_at: str
    ocr_result: CedulaOcrResponse | None = None


@router.post("/cedula-ocr", response_model=CedulaDocumentResponse)
async def upload_and_process_cedula(
    document_side: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> CedulaDocumentResponse:
    """
    Upload a Cédula (ID card) image and process OCR.
    Automatically compares extracted data with customer registration data.
    """
    from app.models.cedula_ocr_result import CedulaOcrResult
    from app.services.cedula_ocr import (
        extract_cedula_data,
        compare_cedula_with_customer,
    )
    from app.config import settings

    if document_side not in ("front", "back"):
        raise HTTPException(
            status_code=400, detail="document_side must be 'front' or 'back'"
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    customer = await get_customer_or_404(current_user, session)

    ext = "." + (file.filename.split(".")[-1].lower() if file.filename else "jpg")
    file_content = await file.read()
    file_size = len(file_content)

    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = await storage_service.upload(
        file_content,
        unique_name,
        folder="customer_documents",
    )

    customer_doc_type = (
        DocumentType.CEDULA_FRONT
        if document_side == "front"
        else DocumentType.CEDULA_BACK
    )

    existing_doc = None
    if document_side == "front":
        result = await session.execute(
            select(CustomerDocument).where(
                CustomerDocument.customer_id == customer.id,
                CustomerDocument.document_type.in_(
                    [DocumentType.CEDULA_FRONT, DocumentType.CEDULA_BACK]
                ),
            )
        )
        existing_doc = result.scalar_one_or_none()

    if existing_doc:
        try:
            await storage_service.delete(existing_doc.file_path)
        except Exception:
            pass
        existing_doc.file_name = file.filename or unique_name
        existing_doc.file_path = file_path
        existing_doc.file_size = file_size
        existing_doc.mime_type = file.content_type
        existing_doc.status = "pending"
        document = existing_doc
    else:
        document = CustomerDocument(
            customer_id=customer.id,
            document_type=customer_doc_type,
            file_name=file.filename or unique_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type,
            status="processing",
        )
        session.add(document)

    await session.flush()

    ocr_result = CedulaOcrResult(
        customer_id=customer.id,
        document_side=document_side,
        file_path=file_path,
        status=OcrStatus.PENDING,
        confidence_score=0.0,
    )
    session.add(ocr_result)
    await session.flush()

    comparison_result = None
    extracted_data = {}

    if settings.ocr_enabled:
        try:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(file_content)
                    temp_path = tmp.name

                from app.services.ocr_service import _process_ocr_result

                loop = asyncio.get_event_loop()
                ocr_raw = await loop.run_in_executor(
                    ThreadPoolExecutor(max_workers=1),
                    lambda: _process_ocr_result(temp_path),
                )

                raw_text = ocr_raw.get("raw_text", "")
                confidence = ocr_raw.get("confidence", 0.0)

                extracted_data = extract_cedula_data(raw_text)

                ocr_result.extracted_text = raw_text
                ocr_result.confidence_score = confidence
                ocr_result.detected_cedula_number = extracted_data.get(
                    "detected_cedula_number"
                )
                ocr_result.detected_name = extracted_data.get("detected_name")
                ocr_result.detected_last_name = extracted_data.get("detected_last_name")
                ocr_result.detected_birth_date = extracted_data.get(
                    "detected_birth_date"
                )
                ocr_result.detected_nationality = extracted_data.get(
                    "detected_nationality"
                )
                ocr_result.detected_gender = extracted_data.get("detected_gender")
                ocr_result.detected_expiration_date = extracted_data.get(
                    "detected_expiration_date"
                )
                ocr_result.detected_blood_type = extracted_data.get(
                    "detected_blood_type"
                )
                ocr_result.detected_civil_status = extracted_data.get(
                    "detected_civil_status"
                )
                ocr_result.detected_address = extracted_data.get("detected_address")
                ocr_result.detected_municipality = extracted_data.get(
                    "detected_municipality"
                )

                customer_data = {
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "document_number": customer.document_number,
                }
                comparison_result = compare_cedula_with_customer(
                    extracted_data, customer_data
                )

                ocr_result.matches_customer_data = comparison_result["overall_match"]
                ocr_result.verification_notes = (
                    f"Match confidence: {comparison_result['confidence_score']:.0%}"
                )

                if extracted_data["fields_extracted"] >= 3:
                    ocr_result.status = OcrStatus.SUCCESS
                elif extracted_data["fields_extracted"] >= 1:
                    ocr_result.status = OcrStatus.PARTIAL
                else:
                    ocr_result.status = OcrStatus.FAILED
                    ocr_result.error_message = "Failed to extract data from image"

                ocr_result.processed_at = datetime.now(timezone.utc)

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            ocr_result.status = OcrStatus.FAILED
            ocr_result.error_message = str(e)
            ocr_result.processed_at = datetime.now(timezone.utc)
    else:
        ocr_result.status = OcrStatus.FAILED
        ocr_result.error_message = "OCR service not enabled"
        ocr_result.processed_at = datetime.now(timezone.utc)

    document.status = "verified" if ocr_result.matches_customer_data else "pending"

    await session.commit()
    await session.refresh(document)
    await session.refresh(ocr_result)

    ocr_response = None
    if ocr_result.id:
        ocr_response = CedulaOcrResponse(
            id=str(ocr_result.id),
            document_side=ocr_result.document_side,
            status=ocr_result.status.value
            if hasattr(ocr_result.status, "value")
            else str(ocr_result.status),
            confidence_score=ocr_result.confidence_score,
            extracted_data=extracted_data,
            comparison_result=comparison_result,
            matches_customer_data=ocr_result.matches_customer_data,
            verification_notes=ocr_result.verification_notes,
        )

    return CedulaDocumentResponse(
        id=str(document.id),
        document_type=document.document_type.value
        if hasattr(document.document_type, "value")
        else str(document.document_type),
        file_name=document.file_name,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status,
        created_at=document.created_at.isoformat()
        if document.created_at
        else datetime.now(timezone.utc).isoformat(),
        ocr_result=ocr_response,
    )


@router.get("/cedula-ocr", response_model=list[CedulaOcrResponse])
async def get_cedula_ocr_results(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CedulaOcrResponse]:
    """Get all Cédula OCR results for the authenticated customer."""
    from app.models.cedula_ocr_result import CedulaOcrResult
    from app.core.enums import OcrStatus

    customer = await get_customer_or_404(current_user, session)

    result = await session.execute(
        select(CedulaOcrResult)
        .where(CedulaOcrResult.customer_id == customer.id)
        .order_by(CedulaOcrResult.created_at.desc())
    )
    ocr_results = result.scalars().all()

    responses = []
    for ocr in ocr_results:
        extracted_data = {
            "detected_cedula_number": ocr.detected_cedula_number,
            "detected_name": ocr.detected_name,
            "detected_last_name": ocr.detected_last_name,
            "detected_birth_date": ocr.detected_birth_date,
            "detected_nationality": ocr.detected_nationality,
            "detected_gender": ocr.detected_gender,
            "detected_expiration_date": ocr.detected_expiration_date,
            "detected_blood_type": ocr.detected_blood_type,
            "detected_civil_status": ocr.detected_civil_status,
            "detected_address": ocr.detected_address,
            "detected_municipality": ocr.detected_municipality,
        }

        customer_data = {
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "document_number": customer.document_number,
        }

        from app.services.cedula_ocr import compare_cedula_with_customer

        comparison_result = compare_cedula_with_customer(extracted_data, customer_data)

        responses.append(
            CedulaOcrResponse(
                id=str(ocr.id),
                document_side=ocr.document_side,
                status=ocr.status.value
                if hasattr(ocr.status, "value")
                else str(ocr.status),
                confidence_score=ocr.confidence_score,
                extracted_data=extracted_data,
                comparison_result=comparison_result,
                matches_customer_data=ocr.matches_customer_data,
                verification_notes=ocr.verification_notes,
            )
        )

    return responses
