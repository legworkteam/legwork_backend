"""Order endpoints (MEMBER)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.cart.repository import CartRepository
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderDetail,
    OrderSummary,
)
from app.modules.orders.service import OrderService
from app.modules.products.repository import ProductRepository
from app.providers.payments.mock import MockPaymentProvider

router = APIRouter(tags=["orders"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_order_service(session: DbSession) -> OrderService:
    return OrderService(
        session,
        CartRepository(session),
        ProductRepository(session),
        OrderRepository(session),
        MockPaymentProvider(),
    )


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


@router.post(
    "/orders",
    response_model=ApiResponse[CreateOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Place an order (mock payment)",
)
async def create_order(
    request: Request,
    payload: CreateOrderRequest,
    user: CurrentUser,
    service: OrderServiceDep,
) -> ApiResponse[CreateOrderResponse]:
    data = await service.create_order(user.id, payload)
    return success_response(data=data, request=request)


@router.get(
    "/me/orders",
    response_model=ApiResponse[list[OrderSummary]],
    summary="List my orders",
)
async def list_orders(
    request: Request,
    user: CurrentUser,
    service: OrderServiceDep,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[OrderSummary]]:
    data, pagination = await service.list_orders(user.id, cursor=cursor, limit=limit)
    return success_response(data=data, request=request, pagination=pagination)


@router.get(
    "/me/orders/{order_id}",
    response_model=ApiResponse[OrderDetail],
    summary="Get my order detail",
)
async def get_order(
    request: Request,
    order_id: uuid.UUID,
    user: CurrentUser,
    service: OrderServiceDep,
) -> ApiResponse[OrderDetail]:
    data = await service.get_order(user.id, order_id)
    return success_response(data=data, request=request)
