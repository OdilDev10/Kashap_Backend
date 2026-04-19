"""Import all models for Alembic migration generation."""

from app.models.base_model import BaseModel
from app.models.lender import Lender, LenderInvitation, LenderBankAccount
from app.models.user import User
from app.models.customer import Customer
from app.models.customer_lender_link import CustomerLenderLink
from app.models.auth import EmailVerification, PasswordReset, OTP
from app.models.loan_application import LoanApplication
from app.models.loan import Loan, Disbursement, Installment
from app.models.payment import Payment, Voucher, OcrResult, PaymentMatch
from app.models.subscription import Subscription, SubscriptionInvoice
from app.models.notification import Notification
from app.models.customer_document import CustomerDocument
from app.models.client_bank_account import ClientBankAccount
from app.models.support_request import SupportRequest
from app.models.audit_log import AuditLog  # noqa: E402,F401

__all__ = [
    "BaseModel",
    "Lender",
    "LenderInvitation",
    "LenderBankAccount",
    "User",
    "Customer",
    "CustomerLenderLink",
    "EmailVerification",
    "PasswordReset",
    "OTP",
    "LoanApplication",
    "Loan",
    "Disbursement",
    "Installment",
    "Payment",
    "Voucher",
    "OcrResult",
    "PaymentMatch",
    "Subscription",
    "SubscriptionInvoice",
    "Notification",
    "CustomerDocument",
    "ClientBankAccount",
    "SupportRequest",
]
