from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DamageSeverity, DiagnosisProviderKind
from app.modules.owned_products.schemas import CareGuideResponse, RegisteredProductDetail


class DiagnosisJobAcceptedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: uuid.UUID = Field(alias="jobId")


class DamageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    damage_id: uuid.UUID = Field(alias="damageId")
    damage_type: str = Field(alias="damageType")
    area: str
    severity: DamageSeverity
    summary: str
    confidence: float
    repair_needed: bool = Field(alias="repairNeeded")
    sort_order: int = Field(alias="sortOrder")
    created_at: datetime = Field(alias="createdAt")


class DiagnosisDetailSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    diagnosis_id: uuid.UUID = Field(alias="diagnosisId")
    job_id: uuid.UUID = Field(alias="jobId")
    registered_product: RegisteredProductDetail = Field(alias="registeredProduct")
    source_file_id: uuid.UUID = Field(alias="sourceFileId")
    provider: DiagnosisProviderKind
    repair_needed: bool = Field(alias="repairNeeded")
    overall_condition: str = Field(alias="overallCondition")
    summary: str
    damages: list[DamageSchema] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


DiagnosisCareGuideResponse = CareGuideResponse
