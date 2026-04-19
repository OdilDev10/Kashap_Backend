"""Idempotent startup seed for essential development accounts."""

from __future__ import annotations

import logging

from sqlalchemy import select

# Ensure all ORM models are registered before querying.
from app.db import base as _base  # noqa: F401
from app.db.session import AsyncSessionFactory
from app.core.enums import (
    AccountType,
    CustomerStatus,
    LenderStatus,
    LenderType,
    UserRole,
    UserStatus,
)
from app.core.security import hash_password
from app.models.customer import Customer
from app.models.lender import Lender
from app.models.user import User

logger = logging.getLogger("app.seed")
logger.setLevel(logging.INFO)

TEST_USER_PASSWORD = "Test@1234"
SEED_LENDER_EMAIL = "lender@opticredit.app"
SEED_LENDER_DOCUMENT = "40200000001"

SEED_USERS = [
    {
        "email": "odil.martinez@opticredit.app",
        "first_name": "Odil",
        "last_name": "Martinez",
        "account_type": AccountType.INTERNAL,
        "role": UserRole.PLATFORM_ADMIN,
        "status": UserStatus.ACTIVE,
        "use_seed_lender": False,
    },
    {
        "email": "lender@opticredit.app",
        "first_name": "Lender",
        "last_name": "Demo",
        "account_type": AccountType.LENDER,
        "role": UserRole.OWNER,
        "status": UserStatus.ACTIVE,
        "use_seed_lender": True,
    },
    {
        "email": "cliente@opticredit.app",
        "first_name": "Cliente",
        "last_name": "Demo",
        "account_type": AccountType.CUSTOMER,
        "role": UserRole.CUSTOMER,
        "status": UserStatus.ACTIVE,
        "use_seed_lender": False,
    },
]


async def run_startup_seed() -> None:
    """Create/update required dev users without duplicating records."""
    async with AsyncSessionFactory() as session:
        lender_result = await session.execute(
            select(Lender).where(Lender.email == SEED_LENDER_EMAIL)
        )
        lender = lender_result.scalar_one_or_none()

        if lender is None:
            lender = Lender(
                legal_name="OptiCredit Demo SRL",
                commercial_name="OptiCredit Demo",
                lender_type=LenderType.FINANCIAL,
                document_type="RNC",
                document_number=SEED_LENDER_DOCUMENT,
                email=SEED_LENDER_EMAIL,
                phone="8090000000",
                status=LenderStatus.ACTIVE,
                subscription_plan="professional",
            )
            session.add(lender)
            await session.flush()
            logger.info("Startup seed created lender: %s", SEED_LENDER_EMAIL)
        else:
            lender.legal_name = "OptiCredit Demo SRL"
            lender.commercial_name = "OptiCredit Demo"
            lender.lender_type = LenderType.FINANCIAL
            lender.document_type = "RNC"
            lender.document_number = SEED_LENDER_DOCUMENT
            lender.phone = "8090000000"
            lender.status = LenderStatus.ACTIVE
            lender.subscription_plan = "professional"
            logger.info("Startup seed updated lender: %s", SEED_LENDER_EMAIL)

        for seed_user in SEED_USERS:
            stmt = select(User).where(User.email == seed_user["email"])
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    first_name=seed_user["first_name"],
                    last_name=seed_user["last_name"],
                    email=seed_user["email"],
                    password_hash=hash_password(TEST_USER_PASSWORD),
                    account_type=seed_user["account_type"],
                    role=seed_user["role"],
                    status=seed_user["status"],
                    lender_id=lender.id if seed_user["use_seed_lender"] else None,
                )
                session.add(user)
                action = "created"
            else:
                user.first_name = seed_user["first_name"]
                user.last_name = seed_user["last_name"]
                user.password_hash = hash_password(TEST_USER_PASSWORD)
                user.status = seed_user["status"]
                user.account_type = seed_user["account_type"]
                user.role = seed_user["role"]
                user.lender_id = lender.id if seed_user["use_seed_lender"] else None
                action = "updated"

            logger.info("Startup seed %s user: %s", action, seed_user["email"])

            if seed_user["account_type"] == AccountType.CUSTOMER:
                customer_stmt = select(Customer).where(Customer.user_id == user.id)
                customer_result = await session.execute(customer_stmt)
                customer = customer_result.scalar_one_or_none()

                if customer is None:
                    customer = Customer(
                        lender_id=lender.id,
                        user_id=user.id,
                        first_name=seed_user["first_name"],
                        last_name=seed_user["last_name"],
                        document_type="Cédula",
                        document_number="40200000001",
                        phone="8090000000",
                        email=seed_user["email"],
                        status=CustomerStatus.ACTIVE,
                    )
                    session.add(customer)
                    logger.info(
                        "Startup seed created customer profile for: %s",
                        seed_user["email"],
                    )
                else:
                    customer.first_name = seed_user["first_name"]
                    customer.last_name = seed_user["last_name"]
                    customer.status = CustomerStatus.ACTIVE
                    logger.info(
                        "Startup seed updated customer profile for: %s",
                        seed_user["email"],
                    )

        await session.commit()
