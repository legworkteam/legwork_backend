from app.modules.ocr.resolver import ProductCodeResolver
from app.providers.ocr.base import OcrDetection, OcrResult


def test_resolver_normalizes_whitespace_and_uppercases() -> None:
    resolver = ProductCodeResolver()

    candidates = resolver.resolve(
        OcrResult(
            detections=[OcrDetection(text=" demo bag 001 ", confidence=0.95)],
            raw_texts=[" demo bag 001 "],
        )
    )

    assert candidates[0].text == "DEMO-BAG-001"


def test_resolver_removes_noise_and_deduplicates() -> None:
    resolver = ProductCodeResolver()

    candidates = resolver.resolve(
        OcrResult(
            detections=[
                OcrDetection(text="DEMO-BAG-001!!", confidence=0.90),
                OcrDetection(text="DEMO BAG 001", confidence=0.80),
            ],
            raw_texts=["DEMO-BAG-001!!", "DEMO BAG 001"],
        )
    )

    texts = [candidate.text for candidate in candidates]
    assert texts.count("DEMO-BAG-001") == 1


def test_resolver_ranks_by_confidence() -> None:
    resolver = ProductCodeResolver()

    candidates = resolver.resolve(
        OcrResult(
            detections=[
                OcrDetection(text="DEMO-BAG-002", confidence=0.70),
                OcrDetection(text="DEMO-BAG-001", confidence=0.95),
            ],
            raw_texts=["DEMO-BAG-002", "DEMO-BAG-001"],
        )
    )

    assert candidates[0].text == "DEMO-BAG-001"


def test_resolver_creates_ambiguous_character_alternative() -> None:
    resolver = ProductCodeResolver()

    candidates = resolver.resolve(
        OcrResult(
            detections=[OcrDetection(text="DEMO-BAG-OO1", confidence=0.91)],
            raw_texts=["DEMO-BAG-OO1"],
        )
    )

    texts = [candidate.text for candidate in candidates]
    assert "DEMO-BAG-OO1" in texts
    assert "DEMO-BAG-001" in texts


def test_resolver_returns_empty_for_no_candidate_text() -> None:
    resolver = ProductCodeResolver()

    candidates = resolver.resolve(
        OcrResult(
            detections=[OcrDetection(text="!!!", confidence=0.99)],
            raw_texts=["!!!"],
        )
    )

    assert candidates == []
