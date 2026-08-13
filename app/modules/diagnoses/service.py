from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import Principal
from app.core.config import settings
from app.core.enums import DiagnosisProviderKind, FileOwnerType, JobType
from app.core.exceptions import GenerationFailedError, NotFoundError
from app.modules.diagnoses.models import Damage, Diagnosis
from app.modules.diagnoses.repository import DiagnosisRepository
from app.modules.diagnoses.schemas import (
    DiagnosisCareGuideResponse,
    DiagnosisDetailSchema,
    DiagnosisJobAcceptedResponse,
    DamageSchema,
)
from app.modules.files.repository import FileRepository
from app.modules.files.service import FileService
from app.modules.jobs.service import JobService
from app.modules.owned_products.service import OwnedProductService
from app.providers.diagnosis.base import DiagnosisProvider, DiagnosisProviderRequest
from app.storage.base import StorageService
from app.storage.validators import IMAGE_RULE, validate_file_upload
from app.utils.datetime import now_kst


class DiagnosisNotFoundError(NotFoundError):
    code = "DIAGNOSIS_NOT_FOUND"
    message = "Diagnosis not found."


class DiagnosisService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        owned_product_service: OwnedProductService,
        provider: DiagnosisProvider,
        storage: StorageService,
        repository: DiagnosisRepository | None = None,
        file_repository: FileRepository | None = None,
    ) -> None:
        self.session = session
        self.owned_products = owned_product_service
        self.provider = provider
        self.storage = storage
        self.repository = repository or DiagnosisRepository(session)
        self.files = file_repository or FileRepository(session)
        self.file_service = FileService(session, repository=self.files, storage=storage)
        self.jobs = JobService(session)

    async def enqueue_diagnosis(
        self,
        *,
        user_id: uuid.UUID,
        registered_product_id: uuid.UUID,
        image: UploadFile,
        background_tasks: BackgroundTasks,
        simulate_failure: bool = False,
    ) -> DiagnosisJobAcceptedResponse:
        await self.owned_products.get_product(user_id, registered_product_id)

        filename = image.filename or "diagnosis-upload.bin"
        content_type = image.content_type or "application/octet-stream"
        content = await image.read()
        validate_file_upload(
            filename=filename,
            content_type=content_type,
            content=content,
            rule=IMAGE_RULE,
        )

        source_file = await self.file_service.create_private_file(
            owner_type=FileOwnerType.USER,
            owner_id=user_id,
            filename=filename,
            content_type=content_type,
            content=content,
            expires_at=now_kst() + timedelta(hours=settings.diagnosis_source_ttl_hours),
        )
        job = await self.jobs.create_job(
            principal=Principal(kind="member", user_id=user_id),
            job_type=JobType.DIAGNOSIS,
        )
        from app.tasks.diagnosis import run_diagnosis_job

        background_tasks.add_task(
            run_diagnosis_job,
            job_id=job.id,
            user_id=user_id,
            registered_product_id=registered_product_id,
            source_file_id=source_file.id,
            provider=self.provider,
            storage=self.storage,
            simulate_failure=simulate_failure,
        )
        return DiagnosisJobAcceptedResponse(jobId=job.id)

    async def process_job(
        self,
        *,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        registered_product_id: uuid.UUID,
        source_file_id: uuid.UUID,
        simulate_failure: bool = False,
    ) -> dict:
        registered_product = await self.owned_products.get_product(user_id, registered_product_id)
        source_file = await self.files.get_by_id(source_file_id)
        if source_file is None:
            raise NotFoundError("Diagnosis source image not found.")
        if not hasattr(self.storage, "resolve_path"):
            raise GenerationFailedError("Storage path resolution is unavailable.")

        provider_result = await self.provider.diagnose(
            DiagnosisProviderRequest(
                source_image_path=str(self.storage.resolve_path(source_file.path)),  # type: ignore[attr-defined]
                registered_product=registered_product,
                simulate_failure=simulate_failure,
            )
        )
        diagnosis = await self.repository.add(
            Diagnosis(
                user_id=user_id,
                registered_product_id=registered_product_id,
                job_id=job_id,
                source_file_id=source_file_id,
                provider=DiagnosisProviderKind(provider_result.provider),
                repair_needed=provider_result.repair_needed,
                overall_condition=provider_result.overall_condition,
                summary=provider_result.summary,
            )
        )
        damages = [
            Damage(
                diagnosis_id=diagnosis.id,
                damage_type=item.damage_type,
                area=item.area,
                severity=item.severity,
                summary=item.summary,
                confidence=item.confidence,
                repair_needed=item.repair_needed,
                sort_order=index,
            )
            for index, item in enumerate(provider_result.damages)
        ]
        if damages:
            await self.repository.add_damages(damages)
        await self.session.commit()
        return {
            "diagnosisId": str(diagnosis.id),
            "repairNeeded": diagnosis.repair_needed,
            "damageCount": len(damages),
        }

    async def get_diagnosis(
        self,
        *,
        user_id: uuid.UUID,
        diagnosis_id: uuid.UUID,
    ) -> DiagnosisDetailSchema:
        diagnosis = await self.repository.get_owned_by_id(
            diagnosis_id=diagnosis_id,
            user_id=user_id,
        )
        if diagnosis is None:
            raise DiagnosisNotFoundError()
        registered_product = await self.owned_products.get_product(
            user_id,
            diagnosis.registered_product_id,
        )
        damages = await self.repository.list_damages(diagnosis_id=diagnosis.id)
        return DiagnosisDetailSchema(
            diagnosisId=diagnosis.id,
            jobId=diagnosis.job_id,
            registeredProduct=registered_product,
            sourceFileId=diagnosis.source_file_id,
            provider=diagnosis.provider,
            repairNeeded=diagnosis.repair_needed,
            overallCondition=diagnosis.overall_condition,
            summary=diagnosis.summary,
            damages=[
                DamageSchema.model_validate(
                    {
                        "damageId": item.id,
                        "damageType": item.damage_type,
                        "area": item.area,
                        "severity": item.severity,
                        "summary": item.summary,
                        "confidence": item.confidence,
                        "repairNeeded": item.repair_needed,
                        "sortOrder": item.sort_order,
                        "createdAt": item.created_at,
                    }
                )
                for item in damages
            ],
            createdAt=diagnosis.created_at,
            updatedAt=diagnosis.updated_at,
        )

    async def get_care_guide(
        self,
        *,
        user_id: uuid.UUID,
        diagnosis_id: uuid.UUID,
    ) -> DiagnosisCareGuideResponse:
        diagnosis = await self.repository.get_owned_by_id(
            diagnosis_id=diagnosis_id,
            user_id=user_id,
        )
        if diagnosis is None:
            raise DiagnosisNotFoundError()
        return await self.owned_products.get_care_guide(user_id, diagnosis.registered_product_id)
