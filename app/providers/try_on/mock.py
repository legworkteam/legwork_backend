from __future__ import annotations

import asyncio

import cv2
import numpy as np

from app.core.exceptions import GenerationFailedError
from app.providers.try_on.base import TryOnProvider, TryOnProviderRequest, TryOnProviderResult


class MockTryOnProvider(TryOnProvider):
    provider_name = "mock"

    async def generate(self, payload: TryOnProviderRequest) -> TryOnProviderResult:
        return await asyncio.to_thread(self._render, payload)

    def _render(self, payload: TryOnProviderRequest) -> TryOnProviderResult:
        if payload.simulate_failure:
            raise GenerationFailedError("Mock try-on provider failure.")

        canvas = np.full((960, 720, 3), 245, dtype=np.uint8)
        cv2.rectangle(canvas, (40, 40), (680, 920), (45, 45, 45), 4)
        cv2.putText(
            canvas,
            "ATELIER LENS",
            (120, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (20, 20, 20),
            3,
            cv2.LINE_AA,
        )

        lines = [
            f"scope: {payload.scope.value}",
            f"gender: {payload.avatar.gender.value}",
            f"height: {payload.avatar.height_cm:.1f}cm",
            f"weight: {payload.avatar.weight_kg:.1f}kg",
        ]
        if payload.product is not None:
            lines.append(f"product: {payload.product.product_code}")
        if payload.variant_id is not None:
            lines.append(f"variant: {payload.variant_id}")
        if payload.source_image_path:
            lines.append("source: uploaded photo")
        else:
            lines.append("source: avatar parameters")

        y = 240
        for line in lines:
            cv2.putText(
                canvas,
                line,
                (80, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (60, 60, 60),
                2,
                cv2.LINE_AA,
            )
            y += 90

        ok, encoded = cv2.imencode(".png", canvas)
        if not ok:
            raise GenerationFailedError("Failed to encode mock try-on image.")

        return TryOnProviderResult(
            filename="mock-try-on.png",
            content_type="image/png",
            content=encoded.tobytes(),
            provider=self.provider_name,
            metadata={"mode": "mock"},
        )
