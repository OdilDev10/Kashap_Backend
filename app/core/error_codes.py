"""Standardized error codes for the application.

All error codes are prefixed with category for easy filtering:
- AUTH_* : Authentication/authorization errors
- VALIDATION_* : Input validation errors
- BUSINESS_* : Business rule violations
- NOT_FOUND_* : Resource not found errors
- CONFLICT_* : Data conflicts
- PAYMENT_* : Payment-specific errors
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    # Authentication / Authorization (AUTH_*)
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"

    # Validation (VALIDATION_*)
    VALIDATION_GENERIC = "VALIDATION_GENERIC"
    VALIDATION_INVALID_EMAIL = "VALIDATION_INVALID_EMAIL"
    VALIDATION_INVALID_PHONE = "VALIDATION_INVALID_PHONE"
    VALIDATION_INVALID_DOCUMENT = "VALIDATION_INVALID_DOCUMENT"
    VALIDATION_MISSING_REQUIRED_FIELD = "VALIDATION_MISSING_REQUIRED_FIELD"
    VALIDATION_FORMAT_ERROR = "VALIDATION_FORMAT_ERROR"

    # Business rules (BUSINESS_*)
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    BUSINESS_INSUFFICIENT_BALANCE = "BUSINESS_INSUFFICIENT_BALANCE"
    BUSINESS_LOAN_NOT_ACTIVE = "BUSINESS_LOAN_NOT_ACTIVE"
    BUSINESS_INSTALLMENT_ALREADY_PAID = "BUSINESS_INSTALLMENT_ALREADY_PAID"
    BUSINESS_INVALID_INSTALLMENT = "BUSINESS_INVALID_INSTALLMENT"

    # Not found (NOT_FOUND_*)
    NOT_FOUND_GENERIC = "NOT_FOUND_GENERIC"
    NOT_FOUND_USER = "NOT_FOUND_USER"
    NOT_FOUND_LOAN = "NOT_FOUND_LOAN"
    NOT_FOUND_INSTALLMENT = "NOT_FOUND_INSTALLMENT"
    NOT_FOUND_PAYMENT = "NOT_FOUND_PAYMENT"
    NOT_FOUND_LENDER = "NOT_FOUND_LENDER"
    NOT_FOUND_CUSTOMER = "NOT_FOUND_CUSTOMER"

    # Conflicts (CONFLICT_*)
    CONFLICT_GENERIC = "CONFLICT_GENERIC"
    CONFLICT_DUPLICATE_EMAIL = "CONFLICT_DUPLICATE_EMAIL"
    CONFLICT_DUPLICATE_DOCUMENT = "CONFLICT_DUPLICATE_DOCUMENT"
    CONFLICT_STATUS_TRANSITION = "CONFLICT_STATUS_TRANSITION"

    # Payment-specific (PAYMENT_*)
    PAYMENT_VOUCHER_ALREADY_USED = "PAYMENT_VOUCHER_ALREADY_USED"
    PAYMENT_VOUCHER_INVALID = "PAYMENT_VOUCHER_INVALID"
    PAYMENT_VOUCHER_REQUIRED = "PAYMENT_VOUCHER_REQUIRED"
    PAYMENT_AMOUNT_MISMATCH = "PAYMENT_AMOUNT_MISMATCH"
    PAYMENT_INSTALLMENT_NOT_FOUND = "PAYMENT_INSTALLMENT_NOT_FOUND"
    PAYMENT_GENERIC_ERROR = "PAYMENT_GENERIC_ERROR"

    # File/File processing (FILE_*)
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_INVALID_TYPE = "FILE_INVALID_TYPE"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"


# Human-readable messages mapped to error codes
ERROR_MESSAGES: dict[ErrorCode, str] = {
    # Auth
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Credenciales inválidas",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Sesión expirada, por favor inicia sesión nuevamente",
    ErrorCode.AUTH_TOKEN_INVALID: "Token de acceso inválido",
    ErrorCode.AUTH_SESSION_EXPIRED: "Tu sesión ha expirado",
    ErrorCode.AUTH_PERMISSION_DENIED: "No tienes permiso para realizar esta acción",
    # Validation
    ErrorCode.VALIDATION_GENERIC: "Error de validación",
    ErrorCode.VALIDATION_INVALID_EMAIL: "Correo electrónico inválido",
    ErrorCode.VALIDATION_INVALID_PHONE: "Número de teléfono inválido",
    ErrorCode.VALIDATION_INVALID_DOCUMENT: "Número de documento inválido",
    ErrorCode.VALIDATION_MISSING_REQUIRED_FIELD: "Campo requerido faltante",
    ErrorCode.VALIDATION_FORMAT_ERROR: "Formato de datos inválido",
    # Business
    ErrorCode.BUSINESS_RULE_VIOLATION: "Violación de regla de negocio",
    ErrorCode.BUSINESS_INSUFFICIENT_BALANCE: "Balance insuficiente",
    ErrorCode.BUSINESS_LOAN_NOT_ACTIVE: "El préstamo no está activo",
    ErrorCode.BUSINESS_INSTALLMENT_ALREADY_PAID: "Esta cuota ya fue pagada",
    ErrorCode.BUSINESS_INVALID_INSTALLMENT: "Cuota inválida",
    # Not found
    ErrorCode.NOT_FOUND_GENERIC: "Recurso no encontrado",
    ErrorCode.NOT_FOUND_USER: "Usuario no encontrado",
    ErrorCode.NOT_FOUND_LOAN: "Préstamo no encontrado",
    ErrorCode.NOT_FOUND_INSTALLMENT: "Cuota no encontrada",
    ErrorCode.NOT_FOUND_PAYMENT: "Pago no encontrado",
    ErrorCode.NOT_FOUND_LENDER: "Financiera no encontrada",
    ErrorCode.NOT_FOUND_CUSTOMER: "Cliente no encontrado",
    # Conflicts
    ErrorCode.CONFLICT_GENERIC: "Conflicto de datos",
    ErrorCode.CONFLICT_DUPLICATE_EMAIL: "Este correo ya está registrado",
    ErrorCode.CONFLICT_DUPLICATE_DOCUMENT: "Este documento ya está registrado",
    ErrorCode.CONFLICT_STATUS_TRANSITION: "Transición de estado inválida",
    # Payment
    ErrorCode.PAYMENT_VOUCHER_ALREADY_USED: "Esta imagen de comprobante ya fue usada en otro pago. Usa una imagen diferente.",
    ErrorCode.PAYMENT_VOUCHER_INVALID: "El comprobante no es válido",
    ErrorCode.PAYMENT_VOUCHER_REQUIRED: "El comprobante de pago es requerido",
    ErrorCode.PAYMENT_AMOUNT_MISMATCH: "El monto no coincide con la cuota",
    ErrorCode.PAYMENT_INSTALLMENT_NOT_FOUND: "Cuota no encontrada para este pago",
    ErrorCode.PAYMENT_GENERIC_ERROR: "Error procesando el pago",
    # File
    ErrorCode.FILE_TOO_LARGE: "El archivo excede el tamaño máximo permitido",
    ErrorCode.FILE_INVALID_TYPE: "Tipo de archivo no permitido",
    ErrorCode.FILE_UPLOAD_FAILED: "Error al subir el archivo",
    ErrorCode.FILE_NOT_FOUND: "Archivo no encontrado",
}


def get_error_message(code: ErrorCode) -> str:
    """Get human-readable message for an error code."""
    return ERROR_MESSAGES.get(code, str(code))


def get_error_response(code: ErrorCode, detail: str | None = None) -> dict:
    """Build a standardized error response."""
    return {
        "success": False,
        "error": {
            "code": code.value,
            "message": get_error_message(code),
            "detail": detail,
        },
    }
