"""Idempotent startup seed for essential development accounts."""

from __future__ import annotations

import logging

from sqlalchemy import select

# Ensure all ORM models are registered before querying.
from app.db import base as _base  # noqa: F401
from app.db.session import AsyncSessionFactory
from app.core.enums import AccountType, UserRole, UserStatus
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger("app.seed")
logger.setLevel(logging.INFO)

TEST_USER_PASSWORD = "Test@1234"

SEED_USERS = [
    {
        "email": "odil.martinez@opticredit.app",
        "first_name": "Odil",
        "last_name": "Martinez",
        "account_type": AccountType.INTERNAL,
        "role": UserRole.PLATFORM_ADMIN,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "cliente@opticredit.app",
        "first_name": "Cliente",
        "last_name": "Demo",
        "account_type": AccountType.CUSTOMER,
        "role": UserRole.CUSTOMER,
        "status": UserStatus.ACTIVE,
    },
]


async def run_startup_seed() -> None:
    """Create/update required dev users without duplicating records."""
    async with AsyncSessionFactory() as session:
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
                action = "updated"

            logger.info("Startup seed %s user: %s", action, seed_user["email"])

        await session.commit()
