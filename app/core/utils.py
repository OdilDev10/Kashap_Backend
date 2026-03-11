"""Utility functions for loans, payments, and general operations."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List


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

    # Calculate total interest (simple interest: P * r * t / 100)
    # t = number of periods / 12 (for annual rate)
    months_duration = num_installments if frequency == "monthly" else (
        num_installments * 7 / 30.44 if frequency == "weekly" else num_installments * 14 / 30.44
    )
    total_interest = principal * annual_interest_rate / 100 * (months_duration / 12)

    # Base amount per installment
    principal_per_installment = principal / num_installments
    interest_per_installment = total_interest / num_installments

    # Calculate day increment based on frequency
    if frequency == "weekly":
        day_increment = 7
    elif frequency == "biweekly":
        day_increment = 14
    else:  # monthly
        day_increment = 30  # Approximate, will be adjusted

    schedule = []
    current_date = start_date

    for i in range(1, num_installments + 1):
        # Adjust date for monthly to handle month boundaries better
        if frequency == "monthly":
            # Try to maintain day of month
            try:
                current_date = start_date + timedelta(days=30 * (i - 1))
                # Adjust to same day of month if possible
                target_day = start_date.day
                if current_date.day != target_day:
                    # Move to next valid day of month
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    # Get last day of month
                    if next_month.day == 1:
                        last_day = (next_month - timedelta(days=1)).day
                        current_date = current_date.replace(
                            month=(current_date.month % 12) + 1,
                            year=current_date.year if current_date.month < 12 else current_date.year + 1,
                            day=min(target_day, last_day),
                        )
            except ValueError:
                # Fallback: use day increment
                current_date = start_date + timedelta(days=day_increment * (i - 1))
        else:
            current_date = start_date + timedelta(days=day_increment * (i - 1))

        schedule.append(
            {
                "installment_number": i,
                "due_date": current_date,
                "principal_component": Decimal(str(round(principal_per_installment, 2))),
                "interest_component": Decimal(str(round(interest_per_installment, 2))),
                "amount": Decimal(str(round(principal_per_installment + interest_per_installment, 2))),
            }
        )

    return schedule


def generate_loan_number(lender_id: str, sequence: int) -> str:
    """
    Generate unique loan reference number.

    Format: {LENDER_PREFIX}-{YYYY}-{SEQUENCE}
    Example: FIN-2026-00001
    """
    year = datetime.now().year
    # Use first 3 chars of lender_id (or default prefix)
    lender_prefix = lender_id[:3].upper() if lender_id else "GEN"
    return f"{lender_prefix}-{year}-{sequence:05d}"
