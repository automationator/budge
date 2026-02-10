"""Shared keyset pagination utilities for reuse across modules."""

from __future__ import annotations

import base64
import json
from datetime import date
from uuid import UUID

from pydantic import BaseModel

from src.exceptions import BadRequestError


class CursorPage[T](BaseModel):
    """Generic paginated response wrapper."""

    items: list[T]
    next_cursor: str | None = None
    has_more: bool


class DateIdCursor(BaseModel):
    """Cursor for (date, id) keyset pagination."""

    date: date
    id: UUID


def encode_cursor(cursor_date: date, cursor_id: UUID) -> str:
    """Encode a (date, id) cursor to base64 string."""
    data = {"date": cursor_date.isoformat(), "id": str(cursor_id)}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> DateIdCursor:
    """Decode a base64 cursor string to (date, id)."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
        return DateIdCursor(
            date=date.fromisoformat(data["date"]),
            id=UUID(data["id"]),
        )
    except Exception as e:
        raise BadRequestError(detail="Invalid cursor") from e
