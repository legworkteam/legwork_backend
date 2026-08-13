from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import CurrentPrincipal
from app.core.responses import ApiResponse, success_response
from app.modules.products.router import ProductServiceDep
from app.modules.products.schemas import ProductSummary
from app.modules.recommendations.service import RecommendationService
from app.providers.recommendations.base import RecommendationProvider
from app.providers.recommendations.rule_based import RuleBasedRecommendationProvider


router = APIRouter(tags=["recommendations"])


@lru_cache
def get_recommendation_provider() -> RecommendationProvider:
    return RuleBasedRecommendationProvider()


def get_recommendation_service(
    product_service: ProductServiceDep,
    provider: Annotated[RecommendationProvider, Depends(get_recommendation_provider)],
) -> RecommendationService:
    return RecommendationService(product_service=product_service, provider=provider)


RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]


@router.get(
    "/products/{productId}/recommendations",
    response_model=ApiResponse[list[ProductSummary]],
    summary="List recommended products",
)
async def list_recommendations(
    productId: UUID,
    request: Request,
    principal: CurrentPrincipal,
    service: RecommendationServiceDep,
    limit: int = Query(default=10, ge=1, le=20),
) -> ApiResponse[list[ProductSummary]]:
    data = await service.list_recommendations(
        product_id=productId,
        principal=principal,
        limit=limit,
    )
    return success_response(data=data, request=request)
