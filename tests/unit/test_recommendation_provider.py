from uuid import uuid4

from app.modules.products.schemas import ProductDetail, ProductTagInfo, VariantInfo
from app.providers.recommendations.base import RecommendationProviderRequest
from app.providers.recommendations.rule_based import RuleBasedRecommendationProvider


def _detail(
    *,
    code: str,
    category: str,
    tags: list[tuple[str, str]],
    stock: int = 10,
) -> ProductDetail:
    return ProductDetail(
        productId=uuid4(),
        productCode=code,
        name=code,
        description=None,
        category=category,
        basePrice=1000,
        currency="KRW",
        thumbnailFileId=None,
        images=[],
        tags=[ProductTagInfo(tagType=tag_type, tagValue=tag_value) for tag_type, tag_value in tags],
        variants=[VariantInfo(variantId=uuid4(), sku=f"SKU-{code}", color=None, size=None, price=1000, stock=stock)],
    )


async def test_rule_based_provider_scores_and_sorts_deterministically() -> None:
    provider = RuleBasedRecommendationProvider()
    base = _detail(
        code="BASE-001",
        category="bag",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
    )
    top = _detail(
        code="A-001",
        category="apparel",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
    )
    same_product = ProductDetail.model_validate({**base.model_dump(by_alias=True), "productId": str(base.product_id)})
    tie = _detail(
        code="B-001",
        category="apparel",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
    )
    style_only = _detail(
        code="C-001",
        category="bag",
        tags=[("style", "casual")],
    )
    no_stock = _detail(
        code="D-001",
        category="apparel",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
        stock=0,
    )

    ranked = await provider.rank(
        RecommendationProviderRequest(
            base_product=base,
            candidates=[same_product, tie, style_only, no_stock, top],
        )
    )

    assert [item.product.product_code for item in ranked] == ["A-001", "B-001", "C-001"]
    assert ranked[0].score == 100
    assert ranked[2].score == 30


async def test_rule_based_provider_supports_individual_score_components() -> None:
    provider = RuleBasedRecommendationProvider()
    base = _detail(
        code="BASE-001",
        category="bag",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
    )
    category_only = _detail(code="CAT-001", category="apparel", tags=[])
    color_only = _detail(code="COL-001", category="bag", tags=[("color", "black")])
    season_only = _detail(code="SEA-001", category="bag", tags=[("season", "summer")])

    ranked = await provider.rank(
        RecommendationProviderRequest(
            base_product=base,
            candidates=[category_only, color_only, season_only],
        )
    )

    scores = {item.product.product_code: item.score for item in ranked}
    assert scores["CAT-001"] == 40
    assert scores["COL-001"] == 20
    assert scores["SEA-001"] == 10


async def test_rule_based_provider_returns_empty_when_no_scoring_candidates() -> None:
    provider = RuleBasedRecommendationProvider()
    base = _detail(
        code="BASE-001",
        category="bag",
        tags=[("style", "casual")],
    )
    unrelated = _detail(
        code="NONE-001",
        category="bag",
        tags=[("style", "formal")],
    )

    ranked = await provider.rank(
        RecommendationProviderRequest(base_product=base, candidates=[unrelated])
    )

    assert ranked == []
