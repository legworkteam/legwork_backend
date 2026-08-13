from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.modules.products.schemas import ProductDetail


@dataclass(frozen=True)
class RecommendationWeights:
    category: int = 40
    style: int = 30
    color: int = 20
    season: int = 10


@dataclass(frozen=True)
class RankedRecommendation:
    product: ProductDetail
    score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecommendationProviderRequest:
    base_product: ProductDetail
    candidates: list[ProductDetail]
    weights: RecommendationWeights = RecommendationWeights()


class RecommendationProvider(Protocol):
    async def rank(self, payload: RecommendationProviderRequest) -> list[RankedRecommendation]:
        ...
