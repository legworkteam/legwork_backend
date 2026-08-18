import uuid
from datetime import datetime, timezone

import pytest

from app.api.dependencies.pagination import (
    decode_cursor,
    encode_cursor,
    normalize_limit,
    paginate_page,
)
from app.core.exceptions import ValidationError


def test_cursor_roundtrip() -> None:
    when = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    row_id = uuid.uuid4()
    cursor = encode_cursor(when, row_id)
    decoded_when, decoded_id = decode_cursor(cursor)
    assert decoded_when == when
    assert decoded_id == row_id


def test_decode_cursor_none_returns_none_pair() -> None:
    assert decode_cursor(None) == (None, None)


def test_decode_cursor_rejects_garbage() -> None:
    with pytest.raises(ValidationError):
        decode_cursor("not-a-valid-cursor")


def test_normalize_limit_clamps_to_range() -> None:
    assert normalize_limit(0) == 1
    assert normalize_limit(1000) == 50
    assert normalize_limit(20) == 20


def test_paginate_page_splits_extra_row_into_has_next() -> None:
    page, has_next = paginate_page([1, 2, 3], 2)
    assert page == [1, 2]
    assert has_next is True

    page2, has_next2 = paginate_page([1, 2], 2)
    assert page2 == [1, 2]
    assert has_next2 is False
