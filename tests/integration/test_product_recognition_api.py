from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider
from app.core.security import create_access_token, create_guest_token
from app.api.dependencies.auth import Principal, get_principal
from app.modules.guests.models import GuestSession
from app.modules.ocr.router import get_ocr_provider
from app.modules.products.models import Product
from app.modules.users.models import User
from app.providers.ocr.base import OcrDetection, OcrPreprocessVariant, OcrResult
from app.utils.datetime import now_kst


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"jpeg-content"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"png-content"
WEBP_BYTES = b"RIFF1234WEBP" + b"webp-content"


class StubOcrProvider:
    def __init__(self, responses: dict[OcrPreprocessVariant, OcrResult]) -> None:
        self.responses = responses

    async def recognize(self, *, image_path: str, variant: OcrPreprocessVariant = OcrPreprocessVariant.PRIMARY) -> OcrResult:
        return self.responses[variant]


async def _create_product(db_session, product_code: str) -> Product:
    product = Product(
        product_code=product_code,
        name="Demo Bag",
        description="OCR test product",
        category="bag",
        base_price=890000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


async def _create_user(db_session) -> User:
    user = User(
        name="OCR Member",
        email=f"ocr-{uuid4().hex}@example.com",
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


@pytest.mark.asyncio
async def test_product_recognition_guest_jpeg_success(db_session, client: TestClient, test_file_root: Path) -> None:
    guest = await _create_guest_session(db_session)
    await _create_product(db_session, "DEMO-BAG-001")
    client.app.dependency_overrides[get_ocr_provider] = lambda: StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-001", confidence=0.96)],
                raw_texts=["DEMO-BAG-001"],
            )
        }
    )

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.jpg", JPEG_BYTES, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recognizedCode"] == "DEMO-BAG-001"
    assert body["data"]["product"]["productCode"] == "DEMO-BAG-001"
    assert not list((test_file_root / "temporary").rglob("*.*"))
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_product_recognition_member_png_success(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    await _create_product(db_session, "DEMO-BAG-002")
    client.app.dependency_overrides[get_ocr_provider] = lambda: StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-002", confidence=0.95)],
                raw_texts=["DEMO-BAG-002"],
            )
        }
    )

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_access_token(str(user.id))}"},
        files={"image": ("demo.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["product"]["productCode"] == "DEMO-BAG-002"
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_product_recognition_webp_success(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)
    await _create_product(db_session, "DEMO-APPAREL-001")
    client.app.dependency_overrides[get_ocr_provider] = lambda: StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="DEMO-APPAREL-001", confidence=0.93)],
                raw_texts=["DEMO-APPAREL-001"],
            )
        }
    )

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.webp", WEBP_BYTES, "image/webp")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["product"]["productCode"] == "DEMO-APPAREL-001"
    client.app.dependency_overrides.clear()


def test_product_recognition_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/product-recognitions",
        files={"image": ("demo.jpg", JPEG_BYTES, "image/jpeg")},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_product_recognition_requires_image_field(client: TestClient) -> None:
    client.app.dependency_overrides[get_principal] = lambda: Principal(kind="member", user_id=uuid4())
    response = client.post(
        "/api/v1/product-recognitions",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_product_recognition_rejects_unsupported_format(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.gif", b"GIF89a", "image/gif")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.asyncio
async def test_product_recognition_rejects_oversized_file(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)
    oversized_png = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (20 * 1024 * 1024))

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.png", oversized_png, "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_product_recognition_rejects_invalid_signature(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.png", b"not-a-real-png", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.asyncio
async def test_product_recognition_returns_not_detected_when_provider_has_no_candidates(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)
    client.app.dependency_overrides[get_ocr_provider] = lambda: StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(detections=[], raw_texts=[]),
            OcrPreprocessVariant.SECONDARY: OcrResult(detections=[], raw_texts=[]),
        }
    )

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.jpg", JPEG_BYTES, "image/jpeg")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PRODUCT_CODE_NOT_DETECTED"
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_product_recognition_returns_not_found_when_db_has_no_match(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)
    client.app.dependency_overrides[get_ocr_provider] = lambda: StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-404", confidence=0.91)],
                raw_texts=["DEMO-BAG-404"],
            ),
            OcrPreprocessVariant.SECONDARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-404", confidence=0.91)],
                raw_texts=["DEMO-BAG-404"],
            ),
        }
    )

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        files={"image": ("demo.jpg", JPEG_BYTES, "image/jpeg")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_product_recognition_response_uses_product_summary_shape(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    await _create_product(db_session, "DEMO-BAG-003")
    client.app.dependency_overrides[get_ocr_provider] = lambda: StubOcrProvider(
        {
            OcrPreprocessVariant.PRIMARY: OcrResult(
                detections=[OcrDetection(text="DEMO-BAG-003", confidence=0.94)],
                raw_texts=["DEMO-BAG-003"],
            )
        }
    )

    response = client.post(
        "/api/v1/product-recognitions",
        headers={"Authorization": f"Bearer {create_access_token(str(user.id))}"},
        files={"image": ("demo.jpg", JPEG_BYTES, "image/jpeg")},
    )

    product = response.json()["data"]["product"]
    assert set(product.keys()) == {
        "productId",
        "productCode",
        "name",
        "thumbnailFileId",
        "basePrice",
        "currency",
    }
    client.app.dependency_overrides.clear()


def test_product_recognitions_are_exposed_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/product-recognitions" in response.json()["paths"]
