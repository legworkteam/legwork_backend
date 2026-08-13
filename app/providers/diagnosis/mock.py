from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from app.core.enums import DamageSeverity
from app.core.exceptions import InvalidImageError, ProviderError
from app.providers.diagnosis.base import (
    DiagnosisDamageResult,
    DiagnosisProvider,
    DiagnosisProviderRequest,
    DiagnosisProviderResult,
)


AREAS = ("handle", "corner", "surface", "strap", "lining", "sole", "zipper")
DAMAGE_TYPES = ("scratch", "stain", "abrasion", "deformation", "discoloration")
SEVERITIES = (
    DamageSeverity.LOW,
    DamageSeverity.MEDIUM,
    DamageSeverity.HIGH,
)


class MockDiagnosisProvider(DiagnosisProvider):
    provider_name = "mock"

    async def diagnose(self, payload: DiagnosisProviderRequest) -> DiagnosisProviderResult:
        return await asyncio.to_thread(self._diagnose_sync, payload)

    def _diagnose_sync(self, payload: DiagnosisProviderRequest) -> DiagnosisProviderResult:
        if payload.simulate_failure:
            raise ProviderError("Mock diagnosis provider failure.")

        source = Path(payload.source_image_path)
        if not source.exists():
            raise InvalidImageError("Diagnosis source image not found.")

        content = source.read_bytes()
        if not content:
            raise InvalidImageError("Diagnosis source image is empty.")

        digest = hashlib.sha256(
            content + str(payload.registered_product.registration_id).encode("utf-8")
        ).digest()
        damage_count = 1 + (digest[0] % 2)

        damages: list[DiagnosisDamageResult] = []
        for index in range(damage_count):
            area = AREAS[digest[1 + index] % len(AREAS)]
            damage_type = DAMAGE_TYPES[digest[3 + index] % len(DAMAGE_TYPES)]
            severity = SEVERITIES[digest[5 + index] % len(SEVERITIES)]
            confidence = round(0.65 + ((digest[7 + index] % 30) / 100), 2)
            repair_needed = severity in {DamageSeverity.MEDIUM, DamageSeverity.HIGH}
            damages.append(
                DiagnosisDamageResult(
                    damage_type=damage_type,
                    area=area,
                    severity=severity,
                    summary=f"Mock result: {area} {damage_type} ({severity.value}).",
                    confidence=confidence,
                    repair_needed=repair_needed,
                )
            )

        max_severity = max(damages, key=lambda item: SEVERITIES.index(item.severity)).severity
        overall_condition = {
            DamageSeverity.LOW: "good",
            DamageSeverity.MEDIUM: "monitor",
            DamageSeverity.HIGH: "repairRecommended",
        }[max_severity]
        repair_needed = any(item.repair_needed for item in damages)
        summary = (
            "Deterministic mock diagnosis based on the uploaded image bytes and registered product."
        )
        return DiagnosisProviderResult(
            overall_condition=overall_condition,
            repair_needed=repair_needed,
            summary=summary,
            damages=damages,
            provider=self.provider_name,
            metadata={"damageCount": str(len(damages))},
        )
