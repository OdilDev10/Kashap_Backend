"""Centralized backward-compatible schema fixes for existing databases.

This module keeps startup schema reconciliation in one place to avoid
scattered ad-hoc ALTER TABLE statements across the codebase.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


# Keep these fixes idempotent (`IF NOT EXISTS`) and append-only.
SCHEMA_COMPAT_SQL: Sequence[str] = (
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500)
    """,
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS document_type VARCHAR(50)
    """,
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS document_number VARCHAR(50)
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS address_line VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500)
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS owner_cedula VARCHAR(50)
    """,
    """
    ALTER TABLE IF EXISTS client_bank_accounts
    ADD COLUMN IF NOT EXISTS balance NUMERIC(15, 2) NOT NULL DEFAULT 0.00
    """,
    """
    ALTER TABLE IF EXISTS customer_documents
    ADD COLUMN IF NOT EXISTS bank_account_id UUID
    """,
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
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS loan_principal_amount NUMERIC(12, 2)
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS loan_interest_rate NUMERIC(5, 2)
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS loan_installments_count INTEGER
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS loan_frequency VARCHAR(20)
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS loan_first_due_date DATE
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS loan_purpose VARCHAR(500)
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS invitee_name VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS invitee_email VARCHAR(255)
    """,
    """
    ALTER TABLE IF EXISTS lender_invitations
    ADD COLUMN IF NOT EXISTS invitee_phone VARCHAR(30)
    """,
    """
    ALTER TABLE IF EXISTS support_requests
    ADD COLUMN IF NOT EXISTS subject VARCHAR(200)
    """,
    """
    ALTER TABLE IF EXISTS support_requests
    ADD COLUMN IF NOT EXISTS phone VARCHAR(30)
    """,
    """
    ALTER TABLE IF EXISTS support_requests
    ADD COLUMN IF NOT EXISTS category VARCHAR(80)
    """,
    """
    ALTER TABLE IF EXISTS support_requests
    ADD COLUMN IF NOT EXISTS attachments_json TEXT
    """,
    """
    ALTER TABLE IF EXISTS support_requests
    ADD COLUMN IF NOT EXISTS context_json TEXT
    """,
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE
    """,
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ
    """,
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS verified_by UUID
    """,
    """
    ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS verification_notes VARCHAR(500)
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_users_verified_by'
        ) THEN
            ALTER TABLE users
            ADD CONSTRAINT fk_users_verified_by
            FOREIGN KEY (verified_by)
            REFERENCES users(id)
            ON DELETE SET NULL;
        END IF;
    END $$;
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS verified_by UUID
    """,
    """
    ALTER TABLE IF EXISTS lenders
    ADD COLUMN IF NOT EXISTS verification_notes VARCHAR(500)
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_lenders_verified_by'
        ) THEN
            ALTER TABLE lenders
            ADD CONSTRAINT fk_lenders_verified_by
            FOREIGN KEY (verified_by)
            REFERENCES users(id)
            ON DELETE SET NULL;
        END IF;
    END $$;
    """,
    """
    ALTER TABLE IF EXISTS customers
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE
    """,
    """
    ALTER TABLE IF EXISTS customers
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ
    """,
    """
    ALTER TABLE IF EXISTS customers
    ADD COLUMN IF NOT EXISTS verified_by UUID
    """,
    """
    ALTER TABLE IF EXISTS customers
    ADD COLUMN IF NOT EXISTS verification_notes VARCHAR(500)
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_customers_verified_by'
        ) THEN
            ALTER TABLE customers
            ADD CONSTRAINT fk_customers_verified_by
            FOREIGN KEY (verified_by)
            REFERENCES users(id)
            ON DELETE SET NULL;
        END IF;
    END $$;
    """,
)


async def apply_schema_compat_fixes(conn: AsyncConnection) -> None:
    """Apply idempotent schema compatibility fixes for drifted environments."""
    for statement in SCHEMA_COMPAT_SQL:
        await conn.execute(text(statement))
