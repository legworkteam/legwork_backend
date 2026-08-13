from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.dependencies.auth import CurrentPrincipal
from app.core.exceptions import ProviderError
from app.core.responses import ApiResponse, success_response
from app.modules.ocr.schemas import ProductRecognitionResponse
from app.modules.ocr.service import ProductRecognitionService
from app.modules.products.router import ProductServiceDep, get_product_service
from app.providers.ocr.base import OcrProvider
from app.providers.ocr.paddle import PaddleOcrProvider
from app.storage.base import StorageService
from app.storage.local import LocalStorageService


router = APIRouter(tags=["ocr"])


@lru_cache
def _get_cached_ocr_provider() -> PaddleOcrProvider:
    return PaddleOcrProvider()


def get_ocr_provider() -> OcrProvider:
    try:
        return _get_cached_ocr_provider()
    except ProviderError:
        raise
    except Exception as exc:  # pragma: no cover
        raise ProviderError("OCR provider is unavailable.") from exc


@lru_cache
def get_storage_service() -> StorageService:
    return LocalStorageService()


def get_product_recognition_service(
    product_service: ProductServiceDep,
    ocr_provider: Annotated[OcrProvider, Depends(get_ocr_provider)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> ProductRecognitionService:
    return ProductRecognitionService(
        product_service=product_service,
        ocr_provider=ocr_provider,
        storage=storage,
    )


ProductRecognitionServiceDep = Annotated[
    ProductRecognitionService,
    Depends(get_product_recognition_service),
]


@router.post(
    "/product-recognitions",
    response_model=ApiResponse[ProductRecognitionResponse],
    summary="Recognize product code from image",
)
async def recognize_product(
    request: Request,
    _principal: CurrentPrincipal,
    service: ProductRecognitionServiceDep,
    image: UploadFile = File(...),
) -> ApiResponse[ProductRecognitionResponse]:
    data = await service.recognize_product(image)
    return success_response(data=data, request=request)
