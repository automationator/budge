from uuid import UUID

from src.exceptions import BadRequestError, ForbiddenError, NotFoundError


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: UUID | None = None):
        detail = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(detail=detail)


class UsernameAlreadyExistsError(BadRequestError):
    def __init__(self, username: str):
        super().__init__(detail=f"User with username {username} already exists")


class RegistrationDisabledError(ForbiddenError):
    """Raised when registration is disabled and someone tries to register."""

    def __init__(self) -> None:
        super().__init__(detail="Registration is currently disabled")
