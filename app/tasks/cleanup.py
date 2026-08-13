from __future__ import annotations

from app.core.database import AsyncSessionLocal
from app.modules.files.repository import FileRepository
from app.modules.guests.repository import GuestRepository
from app.modules.jobs.repository import JobRepository
from app.modules.try_on.repository import TryOnRepository
from app.storage.base import StorageService
from app.storage.local import LocalStorageService
from app.utils.datetime import now_kst


class CleanupService:
    def __init__(
        self,
        *,
        session,
        storage: StorageService,
        files: FileRepository | None = None,
        try_ons: TryOnRepository | None = None,
        jobs: JobRepository | None = None,
        guests: GuestRepository | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.files = files or FileRepository(session)
        self.try_ons = try_ons or TryOnRepository(session)
        self.jobs = jobs or JobRepository(session)
        self.guests = guests or GuestRepository(session)

    async def cleanup_expired_try_ons(self) -> int:
        expired = await self.try_ons.list_expired_unsaved(now=now_kst())
        count = 0
        for row in expired:
            file_metadata = await self.files.get_by_id(row.result_file_id)
            if file_metadata is not None:
                await self.storage.delete(relative_path=file_metadata.path)
                await self.files.delete(file_metadata)
            await self.try_ons.delete(row)
            count += 1
        await self.session.commit()
        return count

    async def cleanup_expired_files(self) -> int:
        expired = await self.files.list_expired(now=now_kst())
        count = 0
        for row in expired:
            await self.storage.delete(relative_path=row.path)
            await self.files.delete(row)
            count += 1
        await self.session.commit()
        return count

    async def cleanup_expired_jobs(self) -> int:
        expired = await self.jobs.list_expired(now=now_kst())
        count = 0
        for row in expired:
            await self.jobs.delete(row)
            count += 1
        await self.session.commit()
        return count

    async def cleanup_expired_guest_sessions(self) -> int:
        expired = await self.guests.list_expired(now=now_kst())
        count = 0
        for row in expired:
            await self.guests.delete(row)
            count += 1
        await self.session.commit()
        return count

    async def run_once(self) -> dict[str, int]:
        expired_try_ons = await self.cleanup_expired_try_ons()
        expired_files = await self.cleanup_expired_files()
        expired_jobs = await self.cleanup_expired_jobs()
        expired_guest_sessions = await self.cleanup_expired_guest_sessions()
        return {
            "expiredTryOns": expired_try_ons,
            "expiredFiles": expired_files,
            "expiredJobs": expired_jobs,
            "expiredGuestSessions": expired_guest_sessions,
        }


async def run_cleanup_once(storage: StorageService | None = None) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        service = CleanupService(session=session, storage=storage or LocalStorageService())
        return await service.run_once()
