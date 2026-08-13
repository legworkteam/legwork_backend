from uuid import uuid4

from app.api.dependencies.auth import Principal
from app.modules.products.schemas import ProductDetail, ProductSummary
from app.modules.recommendations.service import RecommendationService
from app.providers.recommendations.base import RankedRecommendation


def _detail(code: str) -> ProductDetail:
    return ProductDetail(
        productId=uuid4(),
        productCode=code,
        name=code,
        description=None,
        category="bag",
        basePrice=1000,
        currency="KRW",
        thumbnailFileId=None,
        images=[],
        tags=[],
        variants=[],
    )


class StubProductService:
    def __init__(self, base: ProductDetail, candidates: list[ProductDetail]) -> None:
        self.base = base
        self.candidates = candidates

    async def get_product(self, product_id):
        return self.base

    async def list_recommendation_candidates(self, *, exclude_product_id, limit):
        return self.candidates


class StubProvider:
    async def rank(self, payload):
        return [
            RankedRecommendation(product=item, score=100)
            for item in payload.candidates
        ]


async def test_recommendation_service_caps_guest_limit_to_three() -> None:
    base = _detail("BASE-001")
    candidates = [_detail(f"P-{i:03d}") for i in range(5)]
    service = RecommendationService(
        product_service=StubProductService(base, candidates),
        provider=StubProvider(),
    )

    data = await service.list_recommendations(
        product_id=base.product_id,
        principal=Principal(kind="guest", guest_session_id=uuid4()),
        limit=10,
    )

    assert len(data) == 3


async def test_recommendation_service_caps_member_limit_and_handles_empty_candidates() -> None:
    base = _detail("BASE-001")
    candidates = [_detail(f"P-{i:03d}") for i in range(30)]
    service = RecommendationService(
        product_service=StubProductService(base, candidates),
        provider=StubProvider(),
    )

    data = await service.list_recommendations(
        product_id=base.product_id,
        principal=Principal(kind="member", user_id=uuid4()),
        limit=50,
    )
    assert len(data) == 20

    empty = RecommendationService(
        product_service=StubProductService(base, []),
        provider=StubProvider(),
    )
    empty_data = await empty.list_recommendations(
        product_id=base.product_id,
        principal=Principal(kind="member", user_id=uuid4()),
        limit=10,
    )
    assert empty_data == []
