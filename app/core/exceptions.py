from fastapi import HTTPException


class AppHTTPError(HTTPException):
    def __init__(self, status_code: int, detail: str, headers: dict | None = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class UnauthorizedError(AppHTTPError):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(401, detail, headers={"WWW-Authenticate": "Bearer"})


class ForbiddenError(AppHTTPError):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(403, detail)


class DomainError(Exception):
    """Base domain exception independent of HTTP."""

    def __init__(self, message: str = "A domain error occurred", detail: str | None = None):
        self.message = detail or message
        super().__init__(self.message)


class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found", detail: str | None = None):
        super().__init__(detail or message)


class ConflictError(DomainError):
    def __init__(self, message: str = "Resource conflict", detail: str | None = None):
        super().__init__(detail or message)


class CheckoutError(DomainError):
    """Base error for checkout operations."""
    pass


class EmptyCartError(CheckoutError):
    pass


class InsufficientStockError(CheckoutError):
    def __init__(self, product_name: str):
        self.product_name = product_name
        super().__init__(f"Insufficient stock for {product_name}")
