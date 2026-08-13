"""Product endpoints (GUEST). Reusable ProductService dependency lives here."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentPrincipal
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.products.repository import ProductRepository, RecentProductRepository
from app.modules.products.schemas import ProductDetail, RecentProductItem, VariantInfo
from app.modules.products.service import ProductService, RecentProductService

router = APIRouter(tags=["products"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_product_service(session: DbSession) -> ProductService:
    """Shared factory — other domains depend on this to reach the contract."""
    return ProductService(ProductRepository(session))


def get_recent_product_service(session: DbSession) -> RecentProductService:
    return RecentProductService(
        RecentProductRepository(session), ProductRepository(session)
    )


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
RecentServiceDep = Annotated[RecentProductService, Depends(get_recent_product_service)]


@router.get(
    "/products/{product_id}",
    response_model=ApiResponse[ProductDetail],
    summary="Get product detail",
)
async def get_product(
    request: Request,
    product_id: uuid.UUID,
    service: ProductServiceDep,
    recent: RecentServiceDep,
    principal: CurrentPrincipal,
) -> ApiResponse[ProductDetail]:
    data = await service.get_product(product_id)
    # viewing a product records it as recently viewed for this owner
    await recent.record(
        product_id=product_id,
        user_id=principal.user_id,
        guest_session_id=principal.guest_session_id,
    )
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


@router.get(
    "/recent-products",
    response_model=ApiResponse[list[RecentProductItem]],
    summary="List recently viewed products",
)
async def get_recent_products(
    request: Request,
    recent: RecentServiceDep,
    principal: CurrentPrincipal,
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[RecentProductItem]]:
    data = await recent.list_recent(
        user_id=principal.user_id,
        guest_session_id=principal.guest_session_id,
        limit=limit,
    )
    return success_response(data=data, request=request)
