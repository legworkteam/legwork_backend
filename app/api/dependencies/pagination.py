"""Keyset cursor pagination helpers.

Cursor = base64(iso-timestamp|uuid) of the last row's (sortColumn, id) on the
current page — the same scheme coordis/service.py already uses. Repositories
combine this with an `OR (sortCol < cursor_val, AND(sortCol == cursor_val, id
< cursor_id))` WHERE clause, ordered `sortCol DESC, id DESC`, fetching
`limit + 1` rows so the extra row reveals hasNext without a second query.
"""

import base64
import uuid
from datetime import datetime

from app.core.exceptions import ValidationError

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def encode_cursor(sort_value: datetime, row_id: uuid.UUID) -> str:
    raw = f"{sort_value.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> tuple[datetime | None, uuid.UUID | None]:
    if cursor is None:
        return None, None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        sort_raw, id_raw = raw.split("|", 1)
        return datetime.fromisoformat(sort_raw), uuid.UUID(id_raw)
    except Exception as exc:
        raise ValidationError("유효하지 않은 cursor입니다.") from exc


def normalize_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def paginate_page(items: list, limit: int) -> tuple[list, bool]:
    """Given `limit + 1` fetched rows, split into (page, hasNext)."""
    has_next = len(items) > limit
    return items[:limit], has_next
