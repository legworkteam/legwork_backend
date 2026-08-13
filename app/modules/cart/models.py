"""Cart and CartItem entities (Backend A).

Cart is member-only, at most one per user (userId UNIQUE). Re-adding the same
variant increases quantity (uq on (cartId, variantId)).
"""

import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Cart(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cart"

    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True
    )


class CartItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cartItem"
    __table_args__ = (
        UniqueConstraint("cartId", "variantId", name="uq_cartItem_cartId_variantId"),
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(
        "cartId", ForeignKey("cart.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Soft reference to ProductVariant (validated at add/checkout via ProductService).
    variant_id: Mapped[uuid.UUID] = mapped_column(
        "variantId", ForeignKey("productVariant.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
