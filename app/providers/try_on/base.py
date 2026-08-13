from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.core.enums import Gender, TryOnScope
from app.modules.products.schemas import ProductDetail


@dataclass(frozen=True)
class TryOnAvatarParameters:
    height_cm: float
    weight_kg: float
    gender: Gender


@dataclass(frozen=True)
class TryOnProviderRequest:
    scope: TryOnScope
    avatar: TryOnAvatarParameters
    product: ProductDetail | None = None
    variant_id: UUID | None = None
    source_image_path: str | None = None
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
