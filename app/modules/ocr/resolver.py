from __future__ import annotations

import re
from dataclasses import dataclass

from app.providers.ocr.base import OcrDetection, OcrResult


AMBIGUOUS_CHAR_MAP = {
    "O": "0",
    "I": "1",
    "B": "8",
}


@dataclass(frozen=True)
class ProductCodeCandidate:
    text: str
    confidence: float
    source_text: str
    is_alternative: bool = False


class ProductCodeResolver:
    def resolve(self, result: OcrResult) -> list[ProductCodeCandidate]:
        ordered_candidates: dict[str, ProductCodeCandidate] = {}

        for detection in result.detections:
            self._collect_candidates(
                ordered_candidates,
                source_text=detection.text,
                confidence=detection.confidence,
            )

        joined_text = " ".join(raw for raw in result.raw_texts if raw.strip())
        if joined_text:
            average_confidence = (
                sum(detection.confidence for detection in result.detections) / len(result.detections)
                if result.detections
                else 0.0
            )
            self._collect_candidates(
                ordered_candidates,
                source_text=joined_text,
                confidence=average_confidence,
            )

        return sorted(
            ordered_candidates.values(),
            key=lambda candidate: (candidate.confidence, not candidate.is_alternative, len(candidate.text)),
            reverse=True,
        )

    def _collect_candidates(
        self,
        ordered_candidates: dict[str, ProductCodeCandidate],
        *,
        source_text: str,
        confidence: float,
    ) -> None:
        for text, is_alternative in self._candidate_texts(source_text):
            existing = ordered_candidates.get(text)
            candidate = ProductCodeCandidate(
                text=text,
                confidence=confidence,
                source_text=source_text,
                is_alternative=is_alternative,
            )
            if existing is None or candidate.confidence > existing.confidence:
                ordered_candidates[text] = candidate

    def _candidate_texts(self, text: str) -> list[tuple[str, bool]]:
        normalized = self._normalize(text)
        if not normalized:
            return []

        tokens = [token for token in normalized.split("-") if token]
        if not tokens:
            return []

        candidates: list[tuple[str, bool]] = []
        primary_forms = [
            normalized,
            "-".join(tokens),
            "".join(tokens),
        ]
        for value in primary_forms:
            cleaned = value.strip("-")
            if cleaned and cleaned not in [candidate[0] for candidate in candidates]:
                candidates.append((cleaned, False))

        for base_text, _ in list(candidates):
            for alternative in self._generate_alternatives(base_text):
                if alternative not in [candidate[0] for candidate in candidates]:
                    candidates.append((alternative, True))

        return candidates

    @staticmethod
    def _normalize(text: str) -> str:
        upper = text.upper().strip()
        upper = upper.replace("—", "-").replace("–", "-").replace("_", "-").replace("/", "-")
        upper = re.sub(r"[^A-Z0-9\-\s]", "", upper)
        upper = re.sub(r"\s*-\s*", "-", upper)
        upper = re.sub(r"\s+", "-", upper)
        upper = re.sub(r"-{2,}", "-", upper)
        return upper.strip("-")

    @staticmethod
    def _generate_alternatives(text: str) -> list[str]:
        segments = text.split("-")
        alternatives: set[str] = set()
        for index, segment in enumerate(segments):
            if not segment:
                continue
            if not any(char.isdigit() for char in segment):
                continue
            replaced = "".join(AMBIGUOUS_CHAR_MAP.get(char, char) for char in segment)
            if replaced != segment:
                alt_segments = list(segments)
                alt_segments[index] = replaced
                alternatives.add("-".join(alt_segments))
        return list(alternatives)
