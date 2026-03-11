"""Admin lender CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.core.exceptions import ConflictException
from app.repositories.lender_repo import LenderRepository
from app.schemas.lender import LenderCreate, LenderRead, LenderUpdate, PaginatedResponse


router = APIRouter(prefix="/lenders", tags=["lenders"])


@router.get("", response_model=PaginatedResponse[LenderRead])
async def list_lenders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[LenderRead]:
    """List lenders for platform administrators."""
    repo = LenderRepository(session)
    items, total = await repo.list(skip=skip, limit=limit)
    return PaginatedResponse[LenderRead](items=items, total=total, skip=skip, limit=limit)


@router.get("/{lender_id}", response_model=LenderRead)
async def get_lender(
    lender_id: UUID,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> LenderRead:
    """Return a single lender by id."""
    lender = await LenderRepository(session).get_or_404(lender_id, error_code="LENDER_NOT_FOUND")
    return LenderRead.model_validate(lender)


@router.post("", response_model=LenderRead, status_code=status.HTTP_201_CREATED)
async def create_lender(
    payload: LenderCreate,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> LenderRead:
    """Create a lender record."""
    repo = LenderRepository(session)
    payload_data = payload.model_dump()
    payload_data["email"] = payload_data["email"].lower().strip()
    payload_data["document_number"] = payload_data["document_number"].strip()

    if await repo.exists_with_identity(
        email=payload_data["email"],
        document_number=payload_data["document_number"],
    ):
        raise ConflictException("A lender with the same email or document number already exists")

    lender = await repo.create(payload_data)
    await session.commit()
    await session.refresh(lender)
    return LenderRead.model_validate(lender)


@router.patch("/{lender_id}", response_model=LenderRead)
async def update_lender(
    lender_id: UUID,
    payload: LenderUpdate,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> LenderRead:
    """Update lender fields."""
    repo = LenderRepository(session)
    lender = await repo.get_or_404(lender_id, error_code="LENDER_NOT_FOUND")
    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data:
        update_data["email"] = update_data["email"].lower().strip()
    if "document_number" in update_data:
        update_data["document_number"] = update_data["document_number"].strip()

    candidate_email = update_data.get("email", lender.email)
    candidate_document = update_data.get("document_number", lender.document_number)

    if await repo.exists_with_identity(
        email=candidate_email,
        document_number=candidate_document,
        exclude_id=lender_id,
    ):
        raise ConflictException("A lender with the same email or document number already exists")

    lender = await repo.update(lender, update_data)
    await session.commit()
    await session.refresh(lender)
    return LenderRead.model_validate(lender)


@router.delete("/{lender_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lender(
    lender_id: UUID,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a lender record."""
    repo = LenderRepository(session)
    lender = await repo.get_or_404(lender_id, error_code="LENDER_NOT_FOUND")
    await repo.delete(lender)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
