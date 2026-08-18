"""Owned product / after-care endpoints (MEMBER)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.owned_products.repository import RegisteredProductRepository
from app.modules.owned_products.schemas import (
    CareGuideResponse,
    RegisteredProductDetail,
    RegisteredProductItem,
    RegisterProductRequest,
)
from app.modules.owned_products.service import OwnedProductService
from app.modules.products.repository import ProductRepository

router = APIRouter(tags=["owned-products"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_owned_product_service(session: DbSession) -> OwnedProductService:
    return OwnedProductService(
        RegisteredProductRepository(session), ProductRepository(session)
    )


OwnedServiceDep = Annotated[OwnedProductService, Depends(get_owned_product_service)]


@router.post(
    "/me/products",
    response_model=ApiResponse[RegisteredProductItem],
    status_code=status.HTTP_201_CREATED,
    summary="Register an existing product by serial",
)
async def register_product(
    request: Request,
    payload: RegisterProductRequest,
    user: CurrentUser,
    service: OwnedServiceDep,
) -> ApiResponse[RegisteredProductItem]:
    data = await service.register(user.id, payload)
    return success_response(data=data, request=request)


@router.get(
    "/me/products",
    response_model=ApiResponse[list[RegisteredProductItem]],
    summary="List my products (purchased + registered)",
)
async def list_products(
    request: Request,
    user: CurrentUser,
    service: OwnedServiceDep,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[RegisteredProductItem]]:
    data, pagination = await service.list_products(user.id, cursor=cursor, limit=limit)
    return success_response(data=data, request=request, pagination=pagination)


@router.get(
    "/me/products/{registration_id}",
    response_model=ApiResponse[RegisteredProductDetail],
    summary="Get my product detail",
)
async def get_product(
    request: Request,
    registration_id: uuid.UUID,
    user: CurrentUser,
    service: OwnedServiceDep,
) -> ApiResponse[RegisteredProductDetail]:
    data = await service.get_product(user.id, registration_id)
    return success_response(data=data, request=request)


@router.get(
    "/me/products/{registration_id}/care-guide",
    response_model=ApiResponse[CareGuideResponse],
    summary="Get care guide for my product",
)
async def get_care_guide(
    request: Request,
    registration_id: uuid.UUID,
    user: CurrentUser,
    service: OwnedServiceDep,
) -> ApiResponse[CareGuideResponse]:
    data = await service.get_care_guide(user.id, registration_id)
    return success_response(data=data, request=request)
