from uuid import UUID

from src.exceptions import ConflictError, NotFoundError


class LocationNotFoundError(NotFoundError):
    def __init__(self, location_id: UUID | None = None):
        detail = (
            f"Location {location_id} not found" if location_id else "Location not found"
        )
        super().__init__(detail=detail)


class DuplicateLocationNameError(ConflictError):
    def __init__(self, name: str):
        super().__init__(
            detail=f"A location named '{name}' already exists in this team"
        )
