"""Custom error classes for API responses."""


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ValidationError(APIError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 422)


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)


class ForbiddenError(APIError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)
