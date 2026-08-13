"""Product endpoints (GUEST). Reusable ProductService dependency lives here."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentPrincipal
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductDetail, VariantInfo
from app.modules.products.service import ProductService

router = APIRouter(tags=["products"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_product_service(session: DbSession) -> ProductService:
    """Shared factory — other domains depend on this to reach the contract."""
    return ProductService(ProductRepository(session))


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


@router.get(
    "/products/{product_id}",
    response_model=ApiResponse[ProductDetail],
    summary="Get product detail",
)
async def get_product(
    request: Request,
    product_id: uuid.UUID,
    service: ProductServiceDep,
    _principal: CurrentPrincipal,
) -> ApiResponse[ProductDetail]:
    data = await service.get_product(product_id)
    return success_response(data=data, request=request)


@router.get(
    "/products/{product_id}/variants",
    response_model=ApiResponse[list[VariantInfo]],
    summary="List available product variants",
)
async def get_variants(
    request: Request,
    product_id: uuid.UUID,
    service: ProductServiceDep,
    _principal: CurrentPrincipal,
) -> ApiResponse[list[VariantInfo]]:
    data = await service.get_available_variants(product_id)
    return success_response(data=data, request=request)
