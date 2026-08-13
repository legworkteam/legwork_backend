from __future__ import annotations

from dataclasses import dataclass

from fastapi import UploadFile

from app.core.exceptions import (
    NotFoundError,
    ProductCodeAmbiguousError,
    ProductCodeNotDetectedError,
)
from app.modules.ocr.resolver import ProductCodeCandidate, ProductCodeResolver
from app.modules.ocr.schemas import ProductRecognitionResponse
from app.modules.products.schemas import ProductSummary
from app.modules.products.service import ProductService
from app.providers.ocr.base import OcrPreprocessVariant, OcrProvider
from app.storage.base import StorageService
from app.storage.paths import build_temporary_path
from app.storage.validators import IMAGE_RULE, validate_file_upload


class ProductRecognitionNotFoundError(NotFoundError):
    code = "PRODUCT_NOT_FOUND"
    message = "OCR 후보에 해당하는 상품을 찾을 수 없습니다."


@dataclass(frozen=True)
class CandidateMatch:
    candidate: ProductCodeCandidate
    product: ProductSummary


class ProductRecognitionService:
    def __init__(
        self,
        *,
        product_service: ProductService,
        ocr_provider: OcrProvider,
        storage: StorageService,
        resolver: ProductCodeResolver | None = None,
    ) -> None:
        self.product_service = product_service
        self.ocr_provider = ocr_provider
        self.storage = storage
        self.resolver = resolver or ProductCodeResolver()

    async def recognize_product(self, image: UploadFile) -> ProductRecognitionResponse:
        filename = image.filename or "ocr-upload.bin"
        content_type = image.content_type or "application/octet-stream"
        content = await image.read()

        validate_file_upload(
            filename=filename,
            content_type=content_type,
            content=content,
            rule=IMAGE_RULE,
        )

        temporary_path = build_temporary_path(purpose="ocr", filename=filename)
        stored = await self.storage.save(relative_path=temporary_path, content=content)

        try:
            first_result = await self.ocr_provider.recognize(
                image_path=str(stored.absolute_path),
                variant=OcrPreprocessVariant.PRIMARY,
            )
            first_candidates = self.resolver.resolve(first_result)
            first_match = await self._match_candidates(first_candidates)
            if first_match is not None:
                return self._build_response(first_match)

            second_candidates: list[ProductCodeCandidate] = []
            if not first_candidates or first_match is None:
                second_result = await self.ocr_provider.recognize(
                    image_path=str(stored.absolute_path),
                    variant=OcrPreprocessVariant.SECONDARY,
                )
                second_candidates = self.resolver.resolve(second_result)
                second_match = await self._match_candidates(
                    self._merge_candidates(first_candidates, second_candidates)
                )
                if second_match is not None:
                    return self._build_response(second_match)

            merged_candidates = self._merge_candidates(first_candidates, second_candidates)
            if not merged_candidates:
                raise ProductCodeNotDetectedError()

            raise ProductRecognitionNotFoundError(
                details={"candidates": [candidate.text for candidate in merged_candidates[:10]]}
            )
        finally:
            await self.storage.delete(relative_path=stored.relative_path)

    async def _match_candidates(
        self,
        candidates: list[ProductCodeCandidate],
    ) -> CandidateMatch | None:
        matches: list[CandidateMatch] = []
        for candidate in candidates:
            product = await self.product_service.find_by_product_code(candidate.text)
            if product is not None:
                matches.append(CandidateMatch(candidate=candidate, product=product))

        if not matches:
            return None

        best = matches[0]
        ambiguous = [
            match
            for match in matches[1:]
            if match.candidate.confidence == best.candidate.confidence
            and match.candidate.text != best.candidate.text
        ]
        if ambiguous:
            raise ProductCodeAmbiguousError(
                details={"candidates": [best.candidate.text, *[match.candidate.text for match in ambiguous]]}
            )

        return best

    @staticmethod
    def _merge_candidates(
        first: list[ProductCodeCandidate],
        second: list[ProductCodeCandidate],
    ) -> list[ProductCodeCandidate]:
        ordered: dict[str, ProductCodeCandidate] = {}
        for candidate in [*first, *second]:
            existing = ordered.get(candidate.text)
            if existing is None or candidate.confidence > existing.confidence:
                ordered[candidate.text] = candidate
        return sorted(
            ordered.values(),
            key=lambda candidate: (candidate.confidence, not candidate.is_alternative, len(candidate.text)),
            reverse=True,
        )

    @staticmethod
    def _build_response(match: CandidateMatch) -> ProductRecognitionResponse:
        return ProductRecognitionResponse(
            recognizedCode=match.candidate.text,
            confidence=round(match.candidate.confidence, 4),
            product=match.product,
        )
