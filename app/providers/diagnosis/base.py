from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.enums import DamageSeverity
from app.modules.owned_products.schemas import RegisteredProductDetail


@dataclass(frozen=True)
class DiagnosisDamageResult:
    damage_type: str
    area: str
    severity: DamageSeverity
    summary: str
    confidence: float
    repair_needed: bool


@dataclass(frozen=True)
class DiagnosisProviderRequest:
    source_image_path: str
    registered_product: RegisteredProductDetail
    simulate_failure: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DiagnosisProviderResult:
    overall_condition: str
    repair_needed: bool
    summary: str
    damages: list[DiagnosisDamageResult]
    provider: str
    metadata: dict[str, str] = field(default_factory=dict)


class DiagnosisProvider(Protocol):
    async def diagnose(self, payload: DiagnosisProviderRequest) -> DiagnosisProviderResult:
        ...
