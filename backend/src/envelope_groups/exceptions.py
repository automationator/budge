from uuid import UUID

from src.exceptions import ConflictError, NotFoundError


class EnvelopeGroupNotFoundError(NotFoundError):
    def __init__(self, envelope_group_id: UUID | None = None):
        detail = (
            f"Envelope group {envelope_group_id} not found"
            if envelope_group_id
            else "Envelope group not found"
        )
        super().__init__(detail=detail)


class DuplicateEnvelopeGroupNameError(ConflictError):
    def __init__(self, name: str):
        super().__init__(
            detail=f"An envelope group named '{name}' already exists in this team"
        )
