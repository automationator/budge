from fastapi import HTTPException

from src.config import settings


def require_e2e_environment() -> bool:
    """Dependency that ensures ENV=e2e.

    Raises 403 if not in e2e environment.
    """
    if settings.env != "e2e":
        raise HTTPException(
            status_code=403,
            detail="Test endpoints only available in e2e environment",
        )
    return True
