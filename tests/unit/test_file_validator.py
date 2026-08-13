import pytest

from app.core.exceptions import ValidationError
from app.storage.validators import IMAGE_MAX_BYTES, IMAGE_RULE, validate_file_upload


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_validate_allowed_image() -> None:
    validate_file_upload(
        filename="photo.jpg",
        content_type="image/jpeg",
        content=JPEG_BYTES,
        rule=IMAGE_RULE,
    )


def test_validate_rejects_oversized_image() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_file_upload(
            filename="photo.png",
            content_type="image/png",
            content=PNG_BYTES + (b"\x00" * IMAGE_MAX_BYTES),
            rule=IMAGE_RULE,
        )

    assert exc_info.value.details == {"field": "file", "code": "FILE_TOO_LARGE", "maxBytes": IMAGE_MAX_BYTES}


def test_validate_rejects_invalid_extension() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_file_upload(
            filename="photo.gif",
            content_type="image/jpeg",
            content=JPEG_BYTES,
            rule=IMAGE_RULE,
        )

    assert exc_info.value.details == {"field": "filename", "code": "UNSUPPORTED_FILE_TYPE"}


def test_validate_rejects_content_type_mismatch() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_file_upload(
            filename="photo.jpg",
            content_type="image/png",
            content=JPEG_BYTES,
            rule=IMAGE_RULE,
        )

    assert exc_info.value.details == {"field": "contentType", "code": "UNSUPPORTED_FILE_TYPE"}


def test_validate_rejects_signature_mismatch() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_file_upload(
            filename="photo.png",
            content_type="image/png",
            content=JPEG_BYTES,
            rule=IMAGE_RULE,
        )

    assert exc_info.value.details == {"field": "file", "code": "UNSUPPORTED_FILE_TYPE"}
