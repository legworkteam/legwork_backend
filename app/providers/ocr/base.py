from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class OcrPreprocessVariant(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass(frozen=True)
class OcrDetection:
    text: str
    confidence: float
    bounding_box: list[tuple[int, int]] | None = None


@dataclass(frozen=True)
class OcrResult:
    detections: list[OcrDetection]
    raw_texts: list[str]
    processing_time_ms: int | None = None


class OcrProvider(Protocol):
    async def recognize(
        self,
        *,
        image_path: str,
        variant: OcrPreprocessVariant = OcrPreprocessVariant.PRIMARY,
    ) -> OcrResult: ...
