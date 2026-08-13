"""Order + mock payment transaction (Backend A).

Flow: validate selected cart items -> recompute amount from live catalog ->
create Order(PENDING) -> PaymentProvider.pay() -> on success: Order(PAID),
decrement stock, delete cart items, create RegisteredProduct(source=purchase).
On payment decline the failed Order/Payment are persisted (no stock change,
cart untouched) and returned with status=failed. All within one request tx.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    OrderStatus,
    PaymentStatus,
    RegisteredProductSource,
)
from app.core.exceptions import NotFoundError
from app.modules.cart.repository import CartRepository
from app.modules.cart.service import InsufficientStockError, VariantUnavailableError
from app.modules.orders.models import OrderItem, Payment
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderDetail,
    OrderItemDetail,
    OrderSummary,
)
from app.modules.owned_products.models import RegisteredProduct
from app.modules.products.repository import ProductRepository
from app.providers.payments.base import PaymentProvider, PaymentRequest
from app.utils.datetime import now_kst


class CartItemsNotFoundError(NotFoundError):
    message = "선택한 장바구니 항목을 찾을 수 없습니다."


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        cart_repository: CartRepository,
        product_repository: ProductRepository,
        order_repository: OrderRepository,
        payment_provider: PaymentProvider,
    ) -> None:
        self.session = session
        self.cart = cart_repository
        self.products = product_repository
        self.orders = order_repository
        self.payment = payment_provider

    async def create_order(
        self, user_id: uuid.UUID, payload: CreateOrderRequest
    ) -> CreateOrderResponse:
        requested_ids = list(dict.fromkeys(payload.cart_item_ids))  # dedupe, keep order
        cart_items = await self.cart.get_items_for_user(requested_ids, user_id)
        if len(cart_items) != len(requested_ids):
            raise CartItemsNotFoundError()

        variants = await self.products.get_variants_by_ids(
            [ci.variant_id for ci in cart_items]
        )
        products = await self.products.get_products_by_ids(
            [v.product_id for v in variants.values()]
        )

        # validate availability/stock and recompute the amount from the catalog
        total = 0
        currency = "KRW"
        plan = []
        for ci in cart_items:
            variant = variants.get(ci.variant_id)
            if variant is None or not variant.active:
                raise VariantUnavailableError()
            if variant.stock < ci.quantity:
                raise InsufficientStockError()
            product = products[variant.product_id]
            line = variant.price * ci.quantity
            total += line
            currency = product.currency
            plan.append((ci, variant, product, line))

        order = await self.orders.add_order(
            user_id=user_id, total_amount=total, currency=currency
        )
        order_lines = []
        for ci, variant, product, line in plan:
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                variant_id=variant.id,
                product_name_snapshot=product.name,
                variant_snapshot={
                    "sku": variant.sku,
                    "color": variant.color,
                    "size": variant.size,
                },
                unit_price=variant.price,
                quantity=ci.quantity,
                line_amount=line,
            )
            await self.orders.add_item(item)
            order_lines.append((item, ci, variant))

        result = await self.payment.pay(
            PaymentRequest(
                order_id=order.id,
                amount=total,
                currency=currency,
                method=payload.payment_method,
            )
        )
        await self.orders.add_payment(
            Payment(
                order_id=order.id,
                provider=result.provider,
                provider_payment_id=result.provider_payment_id,
                amount=total,
                status=PaymentStatus.SUCCESS if result.success else PaymentStatus.FAILED,
                failure_code=result.failure_code,
                failure_message=result.failure_message,
                approved_at=now_kst() if result.success else None,
            )
        )

        if not result.success:
            order.status = OrderStatus.FAILED
            return CreateOrderResponse(
                orderId=order.id,
                orderStatus=OrderStatus.FAILED,
                paymentStatus=PaymentStatus.FAILED,
            )

        # success: finalize order, decrement stock, clear cart, register products
        order.status = OrderStatus.PAID
        order.paid_at = now_kst()
        purchase_day = order.paid_at.date()
        for item, ci, variant in order_lines:
            variant.stock -= ci.quantity
            self.session.add(
                RegisteredProduct(
                    user_id=user_id,
                    product_id=item.product_id,
                    order_item_id=item.id,
                    source=RegisteredProductSource.PURCHASE,
                    purchase_date=purchase_day,
                )
            )
            await self.cart.delete_item(ci)

        return CreateOrderResponse(
            orderId=order.id,
            orderStatus=OrderStatus.PAID,
            paymentStatus=PaymentStatus.SUCCESS,
            paidAmount=total,
            paidAt=order.paid_at,
        )

    async def list_orders(self, user_id: uuid.UUID) -> list[OrderSummary]:
        orders = await self.orders.list_orders_for_user(user_id)
        return [
            OrderSummary(
                orderId=o.id,
                orderStatus=o.status,
                totalAmount=o.total_amount,
                currency=o.currency,
                paidAt=o.paid_at,
                createdAt=o.created_at,
            )
            for o in orders
        ]

    async def get_order(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderDetail:
        order = await self.orders.get_order_for_user(order_id, user_id)
        if order is None:
            raise NotFoundError("주문을 찾을 수 없습니다.")
        items = await self.orders.list_items(order.id)
        payment = await self.orders.latest_payment(order.id)
        return OrderDetail(
            orderId=order.id,
            orderStatus=order.status,
            totalAmount=order.total_amount,
            currency=order.currency,
            paidAt=order.paid_at,
            createdAt=order.created_at,
            paymentStatus=payment.status if payment else None,
            items=[
                OrderItemDetail(
                    productId=i.product_id,
                    variantId=i.variant_id,
                    productName=i.product_name_snapshot,
                    variant=i.variant_snapshot,
                    unitPrice=i.unit_price,
                    quantity=i.quantity,
                    lineAmount=i.line_amount,
                )
                for i in items
            ],
        )
