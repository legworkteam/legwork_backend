from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diagnoses.service import DiagnosisService
from app.modules.files.repository import FileRepository
from app.modules.jobs.service import JobService
from app.modules.owned_products.repository import RegisteredProductRepository
from app.modules.owned_products.service import OwnedProductService
from app.modules.products.repository import ProductRepository
from app.providers.diagnosis.base import DiagnosisProvider
from app.storage.base import StorageService
from app.tasks.job_utils import run_job_with_new_session


async def run_diagnosis_job(
    *,
    job_id: UUID,
    user_id: UUID,
    registered_product_id: UUID,
    source_file_id: UUID,
    provider: DiagnosisProvider,
    storage: StorageService,
    simulate_failure: bool = False,
) -> None:
    async def runner(session: AsyncSession, _job_service: JobService, _job_id: UUID) -> dict:
        service = DiagnosisService(
            session,
            owned_product_service=OwnedProductService(
                RegisteredProductRepository(session),
                ProductRepository(session),
            ),
            provider=provider,
            storage=storage,
            file_repository=FileRepository(session),
        )
        return await service.process_job(
            job_id=_job_id,
            user_id=user_id,
            registered_product_id=registered_product_id,
            source_file_id=source_file_id,
            simulate_failure=simulate_failure,
        )

    await run_job_with_new_session(job_id=job_id, runner=runner)
