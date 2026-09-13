from typing import Any, Optional


class APIException(Exception):
    """Base exception for all application errors."""
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "BAD_REQUEST",
        errors: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.errors = errors
        super().__init__(self.message)


class NotFoundException(APIException):
    def __init__(self, message: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(message=message, status_code=404, error_code=error_code)


class BadRequestException(APIException):
    def __init__(self, message: str = "Bad request", error_code: str = "BAD_REQUEST", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=400, error_code=error_code, errors=errors)


class UnauthorizedException(APIException):
    def __init__(self, message: str = "Could not validate credentials", error_code: str = "UNAUTHORIZED"):
        super().__init__(message=message, status_code=401, error_code=error_code)


class ForbiddenException(APIException):
    def __init__(self, message: str = "Access denied", error_code: str = "FORBIDDEN"):
        super().__init__(message=message, status_code=403, error_code=error_code)


class ConflictException(APIException):
    def __init__(self, message: str = "Resource conflict occurred", error_code: str = "CONFLICT"):
        super().__init__(message=message, status_code=409, error_code=error_code)


class ValidationException(APIException):
    def __init__(self, message: str = "Validation error", error_code: str = "VALIDATION_ERROR", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=422, error_code=error_code, errors=errors)
