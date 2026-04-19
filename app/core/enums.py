from enum import Enum


class LenderType(str, Enum):
    """Tipo de prestamista."""

    FINANCIAL = "financial"
    INDIVIDUAL = "individual"


class LenderStatus(str, Enum):
    """Estado del prestamista en la plataforma."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class UserRole(str, Enum):
    """Rol de usuario del sistema."""

    PLATFORM_ADMIN = "platform_admin"
    OWNER = "owner"
    MANAGER = "manager"
    AGENT = "agent"
    REVIEWER = "reviewer"
    CUSTOMER = "customer"


class UserStatus(str, Enum):
    """Estado del usuario."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class AccountType(str, Enum):
    """Tipo de cuenta principal del usuario."""

    INTERNAL = "internal"
    CUSTOMER = "customer"
    LENDER = "lender"


class CustomerStatus(str, Enum):
    """Estado del cliente."""

    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class LinkStatus(str, Enum):
    """Estado de la vinculación cliente-prestamista."""

    PENDING = "pending"
    LINKED = "linked"
    UNLINKED = "unlinked"


class DocumentKind(str, Enum):
    """Tipo de documento de identidad."""

    ID_FRONT = "id_front"
    ID_BACK = "id_back"
    SELFIE = "selfie"
    LICENSE = "license"
    OTHER = "other"


class DocumentType(str, Enum):
    """Tipo de documento subido por cliente (identificación y estados financieros)."""

    CEDULA_FRONT = "cedula_front"
    CEDULA_BACK = "cedula_back"
    PASSPORT = "passport"
    FINANCIAL_STATEMENT = "financial_statement"
    BANK_STATEMENT = "bank_statement"
    INCOME_PROOF = "income_proof"
    OTHER = "other"


class LenderDocumentType(str, Enum):
    """Tipo de documento legal del prestamista (RNC, licencia, registro)."""

    RNC = "rnc"
    REPRESENTATIVE_ID_FRONT = "representative_id_front"
    REPRESENTATIVE_ID_BACK = "representative_id_back"
    OPERATING_LICENSE = "operating_license"
    TRADE_REGISTRY = "trade_registry"
    TAX_ID = "tax_id"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Estado de validación de documento."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class LoanApplicationStatus(str, Enum):
    """Estado de solicitud de préstamo."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LoanStatus(str, Enum):
    """Estado del préstamo."""

    APPROVED = "approved"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InstallmentStatus(str, Enum):
    """Estado de la cuota."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    REJECTED = "rejected"


class DisbursementMethod(str, Enum):
    """Método de desembolso."""

    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """Estado del pago."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentSource(str, Enum):
    """Origen del pago."""

    CUSTOMER_PORTAL = "customer_portal"
    MANUAL_BACKOFFICE = "manual_backoffice"


class VoucherStatus(str, Enum):
    """Estado del comprobante."""

    UPLOADED = "uploaded"
    PROCESSED = "processed"
    FAILED = "failed"


class OcrStatus(str, Enum):
    """Estado del resultado OCR."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class MatchStatus(str, Enum):
    """Estado de coincidencia de pago."""

    MATCHED = "matched"
    MISMATCH = "mismatch"
    NEEDS_REVIEW = "needs_review"


class SubscriptionStatus(str, Enum):
    """Estado de suscripción."""

    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class InvoiceStatus(str, Enum):
    """Estado de factura de suscripción."""

    PENDING = "pending"
    PAID = "paid"
    VOID = "void"


class NotificationChannel(str, Enum):
    """Canal de notificación."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    """Estado de notificación."""

    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class AuditAction(str, Enum):
    """Acción registrada en audit log."""

    CREATE = "create"
    UPDATE = "update"
    APPROVE = "approve"
    REJECT = "reject"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"


class LogLevel(str, Enum):
    """Nivel de log del sistema."""

    INFO = "info"
    WARN = "warn"
    ERROR = "error"
