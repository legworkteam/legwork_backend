"""OpenAI (gpt-image-1) try-on provider.

Not a true garment-transfer model -- gpt-image-1's images.edit endpoint
composites reference images per a text prompt, so results are an
approximation, not pose-accurate fitting like a dedicated try-on model
(IDM-VTON etc). Chosen because the team already had OpenAI API credit under
a hard same-day deployment deadline, instead of a new Replicate signup.

Only applies to photo try-on (payload.source_image_path set). Avatar-based
try-on has no real person photo to composite against, so it delegates to
MockTryOnProvider unchanged -- this provider is a drop-in TRY_ON_PROVIDER
switch, both scopes keep working.
"""

from __future__ import annotations

import base64
from pathlib import Path

import anyio
from openai import APIError, APITimeoutError, AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import GenerationFailedError
from app.providers.try_on.base import TryOnProvider, TryOnProviderRequest, TryOnProviderResult
from app.providers.try_on.mock import MockTryOnProvider

_PROMPT = (
    "Photorealistic edit: dress the person shown in the first photo in the "
    "garment(s) shown in the following reference image(s). Preserve the "
    "person's face, body proportions, pose, and the original background "
    "exactly. Only change the clothing to match the reference garment(s)."
)

InputImage = tuple[str, bytes, str]


def _content_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


class OpenAITryOnProvider(TryOnProvider):
    provider_name = "openai"

    def __init__(self, *, client: AsyncOpenAI | None = None) -> None:
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self._mock = MockTryOnProvider()

    async def generate(self, payload: TryOnProviderRequest) -> TryOnProviderResult:
        if payload.simulate_failure:
            raise GenerationFailedError("Mock try-on provider failure.")

        if not payload.source_image_path:
            # Avatar-parameters-only request: no person photo to edit against.
            return await self._mock.generate(payload)

        images = await self._collect_input_images(payload)

        try:
            response = await self._client.images.edit(
                model=settings.openai_image_model,
                image=images,
                prompt=_PROMPT,
                input_fidelity="high",
                quality=settings.openai_image_quality,
                output_format="png",
            )
        except APITimeoutError as exc:
            raise GenerationFailedError("OpenAI try-on 요청이 시간 초과되었습니다.") from exc
        except APIError as exc:
            raise GenerationFailedError(f"OpenAI try-on 생성에 실패했습니다: {exc}") from exc

        if not response.data or not response.data[0].b64_json:
            raise GenerationFailedError("OpenAI가 결과 이미지를 반환하지 않았습니다.")

        content = base64.b64decode(response.data[0].b64_json)
        return TryOnProviderResult(
            filename="openai-try-on.png",
            content_type="image/png",
            content=content,
            provider=self.provider_name,
            metadata={"mode": "openai", "quality": settings.openai_image_quality},
        )

    @staticmethod
    async def _collect_input_images(payload: TryOnProviderRequest) -> list[InputImage]:
        images: list[InputImage] = []
        # Person photo goes first: gpt-image-1 preserves the richest detail
        # (face/identity) for the first reference image in a multi-image edit.
        person_path = Path(payload.source_image_path)  # type: ignore[arg-type]
        person_bytes = await anyio.to_thread.run_sync(person_path.read_bytes)
        images.append((person_path.name, person_bytes, _content_type_for(person_path)))

        for garment_path_str in payload.garment_image_paths[:4]:
            garment_path = Path(garment_path_str)
            if not await anyio.to_thread.run_sync(garment_path.exists):
                continue
            garment_bytes = await anyio.to_thread.run_sync(garment_path.read_bytes)
            images.append((garment_path.name, garment_bytes, _content_type_for(garment_path)))

        return images
