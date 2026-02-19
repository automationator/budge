from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings


def _key_func(request):
    """Extract client IP, falling back to 'test' for test environments."""
    if request.client:
        return get_remote_address(request)
    return "test"


limiter = Limiter(
    key_func=_key_func,
    enabled=settings.env == "production",
)
