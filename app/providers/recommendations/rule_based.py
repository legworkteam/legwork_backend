from __future__ import annotations

from collections.abc import Iterable

from app.modules.products.schemas import ProductDetail
from app.providers.recommendations.base import (
    RankedRecommendation,
    RecommendationProvider,
    RecommendationProviderRequest,
)


CATEGORY_COMPLEMENTS: dict[str, set[str]] = {
    "bag": {"apparel", "accessory"},
    "apparel": {"bag", "accessory", "shoes"},
    "accessory": {"bag", "apparel"},
    "shoes": {"apparel"},
}

COLOR_HARMONIES: dict[str, set[str]] = {
    "black": {"black", "white", "gray", "beige", "brown"},
    "white": {"white", "black", "gray", "navy", "beige"},
    "gray": {"gray", "black", "white", "navy"},
    "navy": {"navy", "white", "gray", "beige"},
    "beige": {"beige", "brown", "white", "black", "navy"},
    "brown": {"brown", "beige", "black", "cream"},
    "cream": {"cream", "brown", "beige", "white"},
}


def _normalized_tags(product: ProductDetail, tag_type: str) -> set[str]:
    return {
        tag.tag_value.strip().lower()
        for tag in product.tags
        if tag.tag_type.strip().lower() == tag_type and tag.tag_value.strip()
    }


def _has_stock(product: ProductDetail) -> bool:
    return any(variant.stock > 0 for variant in product.variants)


class RuleBasedRecommendationProvider(RecommendationProvider):
    async def rank(self, payload: RecommendationProviderRequest) -> list[RankedRecommendation]:
        base = payload.base_product
        base_style = _normalized_tags(base, "style")
        base_color = _normalized_tags(base, "color")
        base_season = _normalized_tags(base, "season")

        ranked: list[RankedRecommendation] = []
        for candidate in payload.candidates:
            if candidate.product_id == base.product_id:
                continue
            if not candidate.variants or not _has_stock(candidate):
                continue

            reasons: list[str] = []
            score = 0

            if self._category_match(base.category, candidate.category):
                score += payload.weights.category
                reasons.append("category")

            candidate_style = _normalized_tags(candidate, "style")
            if base_style and candidate_style and base_style.intersection(candidate_style):
                score += payload.weights.style
                reasons.append("style")

            candidate_color = _normalized_tags(candidate, "color")
            if self._color_match(base_color, candidate_color):
                score += payload.weights.color
                reasons.append("color")

            candidate_season = _normalized_tags(candidate, "season")
            if base_season and candidate_season and base_season.intersection(candidate_season):
                score += payload.weights.season
                reasons.append("season")

            if score <= 0:
                continue

            ranked.append(
                RankedRecommendation(
                    product=candidate,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                item.product.product_code.lower(),
                str(item.product.product_id),
            )
        )
        return ranked

    @staticmethod
    def _category_match(base_category: str | None, candidate_category: str | None) -> bool:
        if not base_category or not candidate_category:
            return False
        base_key = base_category.strip().lower()
        candidate_key = candidate_category.strip().lower()
        complements = CATEGORY_COMPLEMENTS.get(base_key, set())
        reverse = CATEGORY_COMPLEMENTS.get(candidate_key, set())
        return candidate_key in complements or base_key in reverse

    @staticmethod
    def _color_match(base_colors: Iterable[str], candidate_colors: Iterable[str]) -> bool:
        base_set = set(base_colors)
        candidate_set = set(candidate_colors)
        if not base_set or not candidate_set:
            return False
        if base_set.intersection(candidate_set):
            return True
        for color in base_set:
            if candidate_set.intersection(COLOR_HARMONIES.get(color, set())):
                return True
        for color in candidate_set:
            if base_set.intersection(COLOR_HARMONIES.get(color, set())):
                return True
        return False
