from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.enums import AuthProvider
from app.core.security import create_access_token, create_guest_token
from app.modules.coordis.models import SavedCoordi
from app.modules.guests.models import GuestSession
from app.modules.products.models import Product, ProductTag, ProductVariant
from app.modules.users.models import User
from app.utils.datetime import now_kst


async def _create_user(db_session, name: str) -> User:
    user = User(
        name=name,
        email=f"{name.lower()}-{uuid4().hex}@example.com",
        auth_provider=AuthProvider.LOCAL,
        provider_user_id=None,
        password_hash="hash",
        phone=None,
        login_fail_count=0,
        locked_until=None,
        deleted_at=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_guest_session(db_session) -> GuestSession:
    guest = GuestSession(
        expires_at=now_kst() + timedelta(hours=2),
        qr_code_id=None,
        height_cm=None,
        weight_kg=None,
        gender=None,
        photo_try_on_count=0,
    )
    db_session.add(guest)
    await db_session.commit()
    await db_session.refresh(guest)
    return guest


async def _create_product(
    db_session,
    *,
    code: str,
    name: str,
    category: str,
    active: bool = True,
    tags: list[tuple[str, str]] | None = None,
    variants: list[tuple[str, int, bool]] | None = None,
) -> Product:
    product = Product(
        product_code=code,
        name=name,
        description=name,
        category=category,
        base_price=1000,
        currency="KRW",
        active=active,
    )
    db_session.add(product)
    await db_session.flush()
    for tag_type, tag_value in tags or []:
        db_session.add(ProductTag(product_id=product.id, tag_type=tag_type, tag_value=tag_value))
    for index, (sku, stock, active_variant) in enumerate(variants or [("SKU", 10, True)]):
        db_session.add(
            ProductVariant(
                product_id=product.id,
                sku=f"{sku}-{uuid4().hex[:6]}",
                color="black",
                size=f"S{index}",
                price=1000,
                stock=stock,
                active=active_variant,
            )
        )
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
async def test_recommendations_api_for_guest_and_member(db_session, client: TestClient) -> None:
    base = await _create_product(
        db_session,
        code="BASE-001",
        name="Base Bag",
        category="bag",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
    )
    for index in range(4):
        await _create_product(
            db_session,
            code=f"REC-00{index}",
            name=f"Rec {index}",
            category="apparel",
            tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
        )
    await _create_product(
        db_session,
        code="REC-NOSTOCK",
        name="No Stock",
        category="apparel",
        tags=[("style", "casual"), ("color", "black"), ("season", "summer")],
        variants=[("NOSTOCK", 0, True)],
    )
    await _create_product(
        db_session,
        code="REC-INACTIVE",
        name="Inactive",
        category="apparel",
        active=False,
        tags=[("style", "casual")],
    )

    guest = await _create_guest_session(db_session)
    guest_response = client.get(
        f"/api/v1/products/{base.id}/recommendations?limit=10",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
    )
    assert guest_response.status_code == 200
    guest_items = guest_response.json()["data"]
    assert len(guest_items) == 3
    assert all(item["productCode"] != "BASE-001" for item in guest_items)

    member = await _create_user(db_session, "RecoMember")
    member_response = client.get(
        f"/api/v1/products/{base.id}/recommendations?limit=20",
        headers={"Authorization": f"Bearer {create_access_token(str(member.id))}"},
    )
    assert member_response.status_code == 200
    member_codes = [item["productCode"] for item in member_response.json()["data"]]
    assert "REC-NOSTOCK" not in member_codes
    assert "REC-INACTIVE" not in member_codes
    assert member_codes == sorted(member_codes)


@pytest.mark.asyncio
async def test_saved_coordi_crud_pagination_and_ownership(db_session, client: TestClient) -> None:
    owner = await _create_user(db_session, "CoordiOwner")
    other = await _create_user(db_session, "CoordiOther")
    product_a = await _create_product(db_session, code="COORDI-A", name="Coordi A", category="bag")
    product_b = await _create_product(db_session, code="COORDI-B", name="Coordi B", category="apparel")
    product_c = await _create_product(db_session, code="COORDI-C", name="Coordi C", category="accessory")

    variants_a = list((await db_session.scalars(select(ProductVariant))).all())
    # use service-facing validation by fetching actual variant ids from DB rows
    variant_a = next(item for item in variants_a if item.product_id == product_a.id)
    variant_b = next(item for item in variants_a if item.product_id == product_b.id)
    variant_c = next(item for item in variants_a if item.product_id == product_c.id)

    token = create_access_token(str(owner.id))
    create_response = client.post(
        "/api/v1/me/coordis",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "내 코디",
            "items": [
                {"productId": str(product_a.id), "variantId": str(variant_a.id)},
                {"productId": str(product_b.id), "variantId": str(variant_b.id)},
            ],
        },
    )
    assert create_response.status_code == 201
    saved_coordi_id = create_response.json()["data"]["savedCoordiId"]
    assert [item["sortOrder"] for item in create_response.json()["data"]["items"]] == [0, 1]

    second = client.post(
        "/api/v1/me/coordis",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "두번째", "items": [{"productId": str(product_c.id), "variantId": str(variant_c.id)}]},
    )
    assert second.status_code == 201
    third = client.post(
        "/api/v1/me/coordis",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "세번째", "items": [{"productId": str(product_b.id), "variantId": str(variant_b.id)}]},
    )
    assert third.status_code == 201

    list_response = client.get(
        "/api/v1/me/coordis?limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 2
    assert list_response.json()["meta"]["pagination"]["hasNext"] is True
    next_cursor = list_response.json()["meta"]["pagination"]["nextCursor"]
    next_page = client.get(
        f"/api/v1/me/coordis?limit=2&cursor={next_cursor}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert next_page.status_code == 200
    assert len(next_page.json()["data"]) == 1

    detail_response = client.get(
        f"/api/v1/me/coordis/{saved_coordi_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["items"][0]["product"]["productCode"] == "COORDI-A"

    invalid_patch = client.patch(
        f"/api/v1/me/coordis/{saved_coordi_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"productId": str(product_a.id), "variantId": str(variant_b.id)}]},
    )
    assert invalid_patch.status_code == 422
    unchanged = client.get(
        f"/api/v1/me/coordis/{saved_coordi_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(unchanged.json()["data"]["items"]) == 2

    patch_response = client.patch(
        f"/api/v1/me/coordis/{saved_coordi_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "주말 코디",
            "items": [{"productId": str(product_c.id), "variantId": str(variant_c.id)}],
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["name"] == "주말 코디"
    assert len(patch_response.json()["data"]["items"]) == 1

    forbidden = client.get(
        f"/api/v1/me/coordis/{saved_coordi_id}",
        headers={"Authorization": f"Bearer {create_access_token(str(other.id))}"},
    )
    assert forbidden.status_code == 404

    delete_response = client.delete(
        f"/api/v1/me/coordis/{saved_coordi_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200

    post_delete_list = client.get(
        "/api/v1/me/coordis",
        headers={"Authorization": f"Bearer {token}"},
    )
    coordi_ids = {item["savedCoordiId"] for item in post_delete_list.json()["data"]}
    assert saved_coordi_id not in coordi_ids
    deleted_row = await db_session.get(SavedCoordi, UUID(saved_coordi_id))
    assert deleted_row.deleted_at is not None


@pytest.mark.asyncio
async def test_full_coordi_try_on_integration(db_session, client: TestClient) -> None:
    owner = await _create_user(db_session, "TryOnCoordiOwner")
    product_a = await _create_product(db_session, code="FULL-A", name="Full A", category="bag")
    product_b = await _create_product(db_session, code="FULL-B", name="Full B", category="apparel")
    variants = list((await db_session.scalars(select(ProductVariant))).all())
    variant_a = next(item for item in variants if item.product_id == product_a.id)
    variant_b = next(item for item in variants if item.product_id == product_b.id)

    token = create_access_token(str(owner.id))
    coordi_response = client.post(
        "/api/v1/me/coordis",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Full Coordi",
            "items": [
                {"productId": str(product_a.id), "variantId": str(variant_a.id)},
                {"productId": str(product_b.id), "variantId": str(variant_b.id)},
            ],
        },
    )
    saved_coordi_id = coordi_response.json()["data"]["savedCoordiId"]

    avatar_try_on = client.post(
        "/api/v1/avatar-try-ons",
        headers={"Authorization": f"Bearer {token}"},
        json={"scope": "fullCoordi", "savedCoordiId": saved_coordi_id},
    )
    assert avatar_try_on.status_code == 202
    job_id = avatar_try_on.json()["data"]["jobId"]
    job_response = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == "succeeded"

    photo_try_on = client.post(
        "/api/v1/try-ons",
        headers={"Authorization": f"Bearer {token}"},
        data={"scope": "fullCoordi", "savedCoordiId": saved_coordi_id},
        files={"photo": ("person.jpg", b"\xff\xd8\xff\xe0photo", "image/jpeg")},
    )
    assert photo_try_on.status_code == 202
    photo_job = client.get(
        f"/api/v1/jobs/{photo_try_on.json()['data']['jobId']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert photo_job.status_code == 200
    assert photo_job.json()["data"]["status"] == "succeeded"
