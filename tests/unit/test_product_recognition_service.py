from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.core.exceptions import ProductCodeNotDetectedError
from app.modules.ocr.service import ProductRecognitionNotFoundError, ProductRecognitionService
from app.modules.products.schemas import ProductSummary
from app.providers.ocr.base import OcrDetection, OcrPreprocessVariant, OcrResult
from app.storage.local import LocalStorageService


def _upload_file(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


class StubOcrProvider:
    def __init__(self, responses: dict[OcrPreprocessVariant, OcrResult]) -> None:
        self.responses = responses
        self.calls: list[OcrPreprocessVariant] = []

    async def recognize(self, *, image_path: str, variant: OcrPreprocessVariant = OcrPreprocessVariant.PRIMARY) -> OcrResult:
        self.calls.append(variant)
        return self.responses[variant]


class StubProductService:
    def __init__(self, products_by_code: dict[str, ProductSummary | None]) -> None:
        self.products_by_code = products_by_code
        self.calls: list[str] = []

    async def find_by_product_code(self, product_code: str) -> ProductSummary | None:
        self.calls.append(product_code)
        return self.products_by_code.get(product_code)


def _product_summary(product_code: str) -> ProductSummary:
    return ProductSummary(
        productId=uuid4(),
        productCode=product_code,
        name="Demo Bag",
        thumbnailFileId=None,
        basePrice=890000,
        currency="KRW",
    )


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"unit-test"


@pytest.mark.asyncio
async def test_service_falls_back_to_second_candidate(tmp_path: Path) -> None:
    product = _product_summary("DEMO-BAG-001")
    provider = StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-OO1", confidence=0.97)],
                raw_texts=["DEMO-BAG-OO1"],
            )
        }
    )
    service = ProductRecognitionService(
        product_service=StubProductService(
            {
                "DEMO-BAG-OO1": None,
                "DEMO-BAG-001": product,
            }
        ),
        ocr_provider=provider,
        storage=LocalStorageService(tmp_path),
    )

    response = await service.recognize_product(_upload_file("demo.jpg", "image/jpeg", JPEG_BYTES))

    assert response.recognized_code == "DEMO-BAG-001"
    assert response.product.product_code == "DEMO-BAG-001"
    assert provider.calls == [OcrPreprocessVariant.PRIMARY]


@pytest.mark.asyncio
async def test_service_runs_secondary_ocr_when_first_pass_has_no_match(tmp_path: Path) -> None:
    product = _product_summary("DEMO-BAG-002")
    provider = StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="UNKNOWN-001", confidence=0.90)],
                raw_texts=["UNKNOWN-001"],
            ),
            OcrPreprocessVariant.SECONDARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-002", confidence=0.88)],
                raw_texts=["DEMO-BAG-002"],
            ),
        }
    )
    service = ProductRecognitionService(
        product_service=StubProductService(
            {
                "UNKNOWN-001": None,
                "DEMO-BAG-002": product,
            }
        ),
        ocr_provider=provider,
        storage=LocalStorageService(tmp_path),
    )

    response = await service.recognize_product(_upload_file("demo.png", "image/png", b"\x89PNG\r\n\x1a\nservice"))

    assert response.recognized_code == "DEMO-BAG-002"
    assert provider.calls == [OcrPreprocessVariant.PRIMARY, OcrPreprocessVariant.SECONDARY]


@pytest.mark.asyncio
async def test_service_raises_not_found_when_all_candidates_miss(tmp_path: Path) -> None:
    provider = StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="UNKNOWN-001", confidence=0.90)],
                raw_texts=["UNKNOWN-001"],
            ),
            OcrPreprocessVariant.SECONDARY: OcrResult(
                detections=[OcrDetection(text="UNKNOWN-002", confidence=0.80)],
                raw_texts=["UNKNOWN-002"],
            ),
        }
    )
    service = ProductRecognitionService(
        product_service=StubProductService(
            {
                "UNKNOWN-001": None,
                "UNKNOWN-002": None,
            }
        ),
        ocr_provider=provider,
        storage=LocalStorageService(tmp_path),
    )

    with pytest.raises(ProductRecognitionNotFoundError) as exc_info:
        await service.recognize_product(_upload_file("demo.webp", "image/webp", b"RIFFxxxxWEBPpayload"))

    assert exc_info.value.code == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_service_raises_not_detected_when_no_candidates_exist(tmp_path: Path) -> None:
    provider = StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(detections=[], raw_texts=[]),
            OcrPreprocessVariant.SECONDARY: OcrResult(detections=[], raw_texts=[]),
        }
    )
    service = ProductRecognitionService(
        product_service=StubProductService({}),
        ocr_provider=provider,
        storage=LocalStorageService(tmp_path),
    )

    with pytest.raises(ProductCodeNotDetectedError):
        await service.recognize_product(_upload_file("demo.jpg", "image/jpeg", JPEG_BYTES))
