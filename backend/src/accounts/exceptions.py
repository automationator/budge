from uuid import UUID

from src.exceptions import ConflictError, NotFoundError


class AccountNotFoundError(NotFoundError):
    def __init__(self, account_id: UUID | None = None):
        detail = (
            f"Account {account_id} not found" if account_id else "Account not found"
        )
        super().__init__(detail=detail)


class DuplicateAccountNameError(ConflictError):
    def __init__(self, name: str):
        super().__init__(
            detail=f"An account named '{name}' already exists in this team"
        )
