from uuid import UUID

from src.exceptions import BadRequestError, ConflictError, NotFoundError


class EnvelopeNotFoundError(NotFoundError):
    def __init__(self, envelope_id: UUID | None = None):
        detail = (
            f"Envelope {envelope_id} not found" if envelope_id else "Envelope not found"
        )
        super().__init__(detail=detail)


class DuplicateEnvelopeNameError(ConflictError):
    def __init__(self, name: str):
        super().__init__(
            detail=f"An envelope named '{name}' already exists in this team"
        )


class CannotModifyUnallocatedEnvelopeError(BadRequestError):
    def __init__(self, action: str = "modify"):
        super().__init__(detail=f"Cannot {action} the Unallocated envelope")


class CannotDeleteUnallocatedEnvelopeError(BadRequestError):
    def __init__(self):
        super().__init__(detail="Cannot delete the Unallocated envelope")


class CannotDeactivateUnallocatedEnvelopeError(BadRequestError):
    def __init__(self):
        super().__init__(detail="Cannot deactivate the Unallocated envelope")


class InsufficientUnallocatedFundsError(BadRequestError):
    def __init__(self, available: int, requested: int):
        super().__init__(
            detail=f"Insufficient unallocated funds. Available: {available}, Requested: {requested}"
        )


class CannotDeleteCCEnvelopeError(BadRequestError):
    def __init__(self):
        super().__init__(
            detail="Cannot delete a credit card envelope. Delete the credit card account instead."
        )
