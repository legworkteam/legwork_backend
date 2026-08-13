"""Cart endpoints (MEMBER)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.cart.repository import CartRepository
from app.modules.cart.schemas import (
    AddCartItemRequest,
    CartResponse,
    UpdateCartItemRequest,
)
from app.modules.cart.service import CartService
from app.modules.products.repository import ProductRepository

router = APIRouter(tags=["cart"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_cart_service(session: DbSession) -> CartService:
    return CartService(CartRepository(session), ProductRepository(session))


CartServiceDep = Annotated[CartService, Depends(get_cart_service)]


@router.post(
    "/cart/items",
    response_model=ApiResponse[CartResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add item to cart",
)
async def add_item(
    request: Request,
    payload: AddCartItemRequest,
    user: CurrentUser,
    service: CartServiceDep,
) -> ApiResponse[CartResponse]:
    data = await service.add_item(user.id, payload)
    return success_response(data=data, request=request)


@router.get("/cart", response_model=ApiResponse[CartResponse], summary="Get my cart")
async def get_cart(
    request: Request, user: CurrentUser, service: CartServiceDep
) -> ApiResponse[CartResponse]:
    data = await service.get_cart(user.id)
    return success_response(data=data, request=request)


@router.patch(
    "/cart/items/{cart_item_id}",
    response_model=ApiResponse[CartResponse],
    summary="Update a cart item",
)
async def update_item(
    request: Request,
    cart_item_id: uuid.UUID,
    payload: UpdateCartItemRequest,
    user: CurrentUser,
    service: CartServiceDep,
) -> ApiResponse[CartResponse]:
    data = await service.update_item(user.id, cart_item_id, payload)
    return success_response(data=data, request=request)


@router.delete(
    "/cart/items/{cart_item_id}",
    response_model=ApiResponse[CartResponse],
    summary="Remove a cart item",
)
async def delete_item(
    request: Request,
    cart_item_id: uuid.UUID,
    user: CurrentUser,
    service: CartServiceDep,
) -> ApiResponse[CartResponse]:
    data = await service.delete_item(user.id, cart_item_id)
    return success_response(data=data, request=request)
