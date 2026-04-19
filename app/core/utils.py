"""Utility functions for loans, payments, and general operations."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from enum import Enum


class CodePrefix(str, Enum):
    """Prefixes for different entity types."""

    LOAN = "LOAN"
    PAYMENT = "PAY"
    APPLICATION = "APP"
    CUSTOMER = "CUST"
    USER = "USR"


def generate_code(prefix: CodePrefix, sequence: int, year: int | None = None) -> str:
    """
    Generate a unique sequential code for any entity.

    Format: {PREFIX}-{YEAR}-{SEQUENCE:05d}
    Examples:
        LOAN-2026-00001
        PAY-2026-00042
        APP-2026-00003
        CUST-2026-00015
        USR-2026-00008
    """
    if year is None:
        year = datetime.now().year
    return f"{prefix.value}-{year}-{sequence:05d}"


def generate_loan_number(
    sequence: int, lender_prefix: str = "LOAN", year: int | None = None
) -> str:
    """Generate unique loan reference number."""
    return generate_code(CodePrefix.LOAN, sequence, year).replace(
        "LOAN", lender_prefix.upper(), 1
    )


def generate_payment_number(sequence: int, year: int | None = None) -> str:
    """Generate unique payment reference number."""
    return generate_code(CodePrefix.PAYMENT, sequence, year)


def generate_application_number(sequence: int, year: int | None = None) -> str:
    """Generate unique application reference number."""
    return generate_code(CodePrefix.APPLICATION, sequence, year)


def generate_customer_number(sequence: int, year: int | None = None) -> str:
    """Generate unique customer reference number."""
    return generate_code(CodePrefix.CUSTOMER, sequence, year)


def generate_user_number(sequence: int, year: int | None = None) -> str:
    """Generate unique user reference number."""
    return generate_code(CodePrefix.USER, sequence, year)


def generate_installment_schedule(
    principal: Decimal,
    annual_interest_rate: Decimal,
    num_installments: int,
    frequency: str = "monthly",
    start_date: datetime | None = None,
) -> List[dict]:
    """
    Generate loan installment schedule with simple interest calculation.

    Args:
        principal: Loan amount
        annual_interest_rate: Annual interest rate (as percentage, e.g., 12 for 12%)
        num_installments: Number of installments
        frequency: "weekly", "biweekly", or "monthly"
        start_date: First installment due date (default: today)

    Returns:
        List of dicts with: {
            "installment_number": int,
            "due_date": datetime,
            "principal_component": Decimal,
            "interest_component": Decimal,
            "amount": Decimal,
        }
    """
    if start_date is None:
        start_date = datetime.now()

    months_duration = Decimal(
        str(
            num_installments
            if frequency == "monthly"
            else (
                num_installments * 7 / 30.44
                if frequency == "weekly"
                else num_installments * 14 / 30.44
            )
        )
    )
    total_interest = principal * annual_interest_rate / 100 * (months_duration / 12)

    principal_per_installment = principal / num_installments
    interest_per_installment = total_interest / num_installments

    if frequency == "weekly":
        day_increment = 7
    elif frequency == "biweekly":
        day_increment = 14
    else:
        day_increment = 30

    schedule = []
    current_date = start_date

    for i in range(1, num_installments + 1):
        if frequency == "monthly":
            try:
                current_date = start_date + timedelta(days=30 * (i - 1))
                target_day = start_date.day
                if current_date.day != target_day:
                    if current_date.month == 12:
                        next_month = current_date.replace(
                            year=current_date.year + 1, month=1, day=1
                        )
                    else:
                        next_month = current_date.replace(
                            month=current_date.month + 1, day=1
                        )
                    if next_month.day == 1:
                        last_day = (next_month - timedelta(days=1)).day
                        current_date = current_date.replace(
                            month=(current_date.month % 12) + 1,
                            year=current_date.year
                            if current_date.month < 12
                            else current_date.year + 1,
                            day=min(target_day, last_day),
                        )
            except ValueError:
                current_date = start_date + timedelta(days=day_increment * (i - 1))
        else:
            current_date = start_date + timedelta(days=day_increment * (i - 1))

        schedule.append(
            {
                "installment_number": i,
                "due_date": current_date,
                "principal_component": Decimal(
                    str(round(principal_per_installment, 2))
                ),
                "interest_component": Decimal(str(round(interest_per_installment, 2))),
                "amount": Decimal(
                    str(round(principal_per_installment + interest_per_installment, 2))
                ),
            }
        )

    return schedule
