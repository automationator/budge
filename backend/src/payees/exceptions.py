from uuid import UUID

from src.exceptions import ConflictError, NotFoundError


class PayeeNotFoundError(NotFoundError):
    def __init__(self, payee_id: UUID | None = None):
        detail = f"Payee {payee_id} not found" if payee_id else "Payee not found"
        super().__init__(detail=detail)


class DuplicatePayeeNameError(ConflictError):
    def __init__(self, name: str):
        super().__init__(detail=f"A payee named '{name}' already exists in this team")


class PayeeInUseError(ConflictError):
    def __init__(self, name: str):
        super().__init__(
            detail=f"Cannot delete payee '{name}' because it is linked to existing transactions"
        )
