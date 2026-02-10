from src.exceptions import ForbiddenError


class AdminRequiredError(ForbiddenError):
    """Raised when a non-admin user tries to access admin-only resources."""

    def __init__(self) -> None:
        super().__init__(detail="Admin access required")
