"""Database session management."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    future=True,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database (create tables and apply backward-compatible fixes)."""
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Backward-compatible schema fix for environments with existing table
        # created before `ClientBankAccount.balance` was added to the model.
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500)
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS client_bank_accounts
                ADD COLUMN IF NOT EXISTS balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS customer_documents
                ADD COLUMN IF NOT EXISTS bank_account_id UUID
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS lenders
                ADD COLUMN IF NOT EXISTS address_line VARCHAR(255)
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_customer_documents_bank_account_id'
                    ) THEN
                        ALTER TABLE customer_documents
                        ADD CONSTRAINT fk_customer_documents_bank_account_id
                        FOREIGN KEY (bank_account_id)
                        REFERENCES client_bank_accounts(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )


async def close_db() -> None:
    """Close database connection."""
    await engine.dispose()
