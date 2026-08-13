from __future__ import annotations

import uuid

from app.api.dependencies.auth import Principal
from app.modules.products.schemas import ProductSummary
from app.modules.products.service import ProductService
from app.providers.recommendations.base import RecommendationProvider, RecommendationProviderRequest


DEFAULT_RECOMMENDATION_LIMIT = 10
MAX_MEMBER_RECOMMENDATION_LIMIT = 20
MAX_GUEST_RECOMMENDATION_LIMIT = 3
RECOMMENDATION_CANDIDATE_LIMIT = 50


class RecommendationService:
    def __init__(
        self,
        *,
        product_service: ProductService,
        provider: RecommendationProvider,
    ) -> None:
        self.product_service = product_service
        self.provider = provider

    async def list_recommendations(
        self,
        *,
        product_id: uuid.UUID,
        principal: Principal,
        limit: int = DEFAULT_RECOMMENDATION_LIMIT,
    ) -> list[ProductSummary]:
        requested_limit = max(1, limit)
        effective_limit = min(
            requested_limit,
            MAX_MEMBER_RECOMMENDATION_LIMIT if principal.kind == "member" else MAX_GUEST_RECOMMENDATION_LIMIT,
        )

        base_product = await self.product_service.get_product(product_id)
        candidates = await self.product_service.list_recommendation_candidates(
            exclude_product_id=product_id,
            limit=RECOMMENDATION_CANDIDATE_LIMIT,
        )
        ranked = await self.provider.rank(
            RecommendationProviderRequest(
                base_product=base_product,
                candidates=candidates,
            )
        )
        return [
            ProductSummary(
                productId=item.product.product_id,
                productCode=item.product.product_code,
                name=item.product.name,
                thumbnailFileId=item.product.thumbnail_file_id,
                basePrice=item.product.base_price,
                currency=item.product.currency,
            )
            for item in ranked[:effective_limit]
        ]
