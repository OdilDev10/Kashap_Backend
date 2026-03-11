"""Custom exceptions for the application."""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Recurso no encontrado", code: str = "NOT_FOUND"):
        super().__init__(message, code)


class ForbiddenException(AppException):
    """Raised when a user lacks permissions."""

    def __init__(self, message: str = "No tiene permiso para realizar esta acción", code: str = "FORBIDDEN"):
        super().__init__(message, code)


class ConflictException(AppException):
    """Raised when a resource already exists or state is invalid."""

    def __init__(self, message: str = "Conflicto de datos", code: str = "CONFLICT"):
        super().__init__(message, code)


class BusinessRuleException(AppException):
    """Raised when a business rule is violated."""

    def __init__(self, message: str = "Violación de regla de negocio", code: str = "BUSINESS_RULE_ERROR"):
        super().__init__(message, code)


class UnauthorizedException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "No autenticado", code: str = "UNAUTHORIZED"):
        super().__init__(message, code)


class ValidationException(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Error de validación", code: str = "VALIDATION_ERROR"):
        super().__init__(message, code)
