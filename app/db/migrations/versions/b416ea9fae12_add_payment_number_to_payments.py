"""add_payment_number_to_payments

Revision ID: b416ea9fae12
Revises:
Create Date: 2026-04-19 04:07:22.335316

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b416ea9fae12"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments", sa.Column("payment_number", sa.String(length=50), nullable=True)
    )
    op.create_index(
        op.f("ix_payments_payment_number"),
        "payments",
        ["payment_number"],
        unique=True,
        postgresql_where=(sa.text("payment_number IS NOT NULL")),
    )

    # Update existing payments with a generated payment_number
    # Using id as sequence number since we don't have access to the app's generate_payment_number
    op.execute("""
        UPDATE payments 
        SET payment_number = 'PAY-LEGACY-' || id::text 
        WHERE payment_number IS NULL
    """)

    # Now make it NOT NULL
    op.alter_column("payments", "payment_number", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_payment_number"), table_name="payments")
    op.drop_column("payments", "payment_number")
