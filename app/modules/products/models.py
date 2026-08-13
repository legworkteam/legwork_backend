"""Product catalog entities (Backend A).

Product = 품번 unit (productCode UNIQUE, the OCR lookup key). ProductVariant =
color/size/sku/price/stock. ProductImage.fileId is a soft reference to B's
FileMetadata (no DB-level FK, to keep A/B migrations independent). ProductTag
carries style/color/season values used by recommendations.
"""

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product"

    product_code: Mapped[str] = mapped_column(
        "productCode", String(100), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    base_price: Mapped[int] = mapped_column("basePrice", BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProductVariant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "productVariant"
    __table_args__ = (
        Index("ix_productVariant_productId_active", "productId", "active"),
        Index("ix_productVariant_productId_color_size", "productId", "color", "size"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        "productId", ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[str | None] = mapped_column(String(80), nullable=True)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProductImage(UUIDMixin, Base):
    __tablename__ = "productImage"

    product_id: Mapped[uuid.UUID] = mapped_column(
        "productId", ForeignKey("product.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Soft reference to FileMetadata (owned by Backend B); no FK on purpose.
    file_id: Mapped[uuid.UUID] = mapped_column("fileId", Uuid, nullable=False)
    type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column("sortOrder", Integer, nullable=False, default=0)


class ProductTag(UUIDMixin, Base):
    __tablename__ = "productTag"
    __table_args__ = (Index("ix_productTag_productId", "productId"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        "productId", ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    tag_type: Mapped[str] = mapped_column("tagType", String(40), nullable=False)
    tag_value: Mapped[str] = mapped_column("tagValue", String(80), nullable=False)
