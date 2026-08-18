from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.core.enums import Gender, TryOnScope
from app.modules.products.schemas import ProductDetail, VariantInfo


@dataclass(frozen=True)
class TryOnAvatarParameters:
    height_cm: float
    weight_kg: float
    gender: Gender


@dataclass(frozen=True)
class TryOnCoordiItem:
    product: ProductDetail
    variant: VariantInfo | None = None


@dataclass(frozen=True)
class TryOnProviderRequest:
    scope: TryOnScope
    avatar: TryOnAvatarParameters
    product: ProductDetail | None = None
    variant_id: UUID | None = None
    coordi_items: list[TryOnCoordiItem] = field(default_factory=list)
    source_image_path: str | None = None
    # Absolute paths to garment/product reference images (product's thumbnail,
    # or one per coordi item), resolved by the service layer. Empty when none
    # of the relevant products have a thumbnail on file.
    garment_image_paths: list[str] = field(default_factory=list)
    simulate_failure: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TryOnProviderResult:
    filename: str
    content_type: str
    content: bytes
    provider: str
    metadata: dict[str, str] = field(default_factory=dict)


class TryOnProvider(Protocol):
    async def generate(self, payload: TryOnProviderRequest) -> TryOnProviderResult:
        ...
