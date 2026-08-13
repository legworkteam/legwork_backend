from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import ErrorCode, ValidationError


IMAGE_MAX_BYTES = 20 * 1024 * 1024
VIDEO_MAX_BYTES = 100 * 1024 * 1024

MP4_BRANDS = (b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"mp71")
MOV_BRANDS = (b"qt  ",)


@dataclass(frozen=True)
class FileValidationRule:
    allowed_extensions: set[str]
    allowed_content_types: set[str]
    max_bytes: int
    kind: str


IMAGE_RULE = FileValidationRule(
    allowed_extensions={".jpg", ".jpeg", ".png", ".webp"},
    allowed_content_types={"image/jpeg", "image/png", "image/webp"},
    max_bytes=IMAGE_MAX_BYTES,
    kind="image",
)

VIDEO_RULE = FileValidationRule(
    allowed_extensions={".mp4", ".mov"},
    allowed_content_types={"video/mp4", "video/quicktime"},
    max_bytes=VIDEO_MAX_BYTES,
    kind="video",
)


EXTENSION_TO_CONTENT_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime"},
}


def _matches_signature(extension: str, content_type: str, content: bytes) -> bool:
    if extension in {".jpg", ".jpeg"} or content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png" or content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp" or content_type == "image/webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    if extension == ".mp4" or content_type == "video/mp4":
        return len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in MP4_BRANDS
    if extension == ".mov" or content_type == "video/quicktime":
        return len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in MOV_BRANDS
    return False


def validate_file_upload(
    *,
    filename: str,
    content_type: str,
    content: bytes,
    rule: FileValidationRule,
) -> None:
    extension = Path(filename).suffix.lower()
    if extension not in rule.allowed_extensions:
        raise ValidationError(
            "Unsupported file extension.",
            details={"field": "filename", "code": ErrorCode.UNSUPPORTED_FILE_TYPE},
        )

    expected_content_types = EXTENSION_TO_CONTENT_TYPES.get(extension, set())
    if content_type not in rule.allowed_content_types or content_type not in expected_content_types:
        raise ValidationError(
            "Unsupported content type.",
            details={"field": "contentType", "code": ErrorCode.UNSUPPORTED_FILE_TYPE},
        )

    if len(content) > rule.max_bytes:
        raise ValidationError(
            "File size exceeds the allowed limit.",
            details={"field": "file", "code": ErrorCode.FILE_TOO_LARGE, "maxBytes": rule.max_bytes},
        )

    if not _matches_signature(extension, content_type, content):
        raise ValidationError(
            "File signature does not match the declared file type.",
            details={"field": "file", "code": ErrorCode.UNSUPPORTED_FILE_TYPE},
        )
