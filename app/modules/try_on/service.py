from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import Principal
from app.core.config import settings
from app.core.enums import FileOwnerType, Gender, JobType, TryOnProviderKind, TryOnScope
from app.core.exceptions import ForbiddenError, GenerationFailedError, GuestLimitExceededError, NotFoundError, ValidationError
from app.modules.avatars.repository import AvatarRepository
from app.modules.coordis.repository import SavedCoordiRepository
from app.modules.coordis.service import SavedCoordiService
from app.modules.files.repository import FileRepository
from app.modules.files.service import FileService
from app.modules.guests.repository import GuestRepository
from app.modules.jobs.service import JobService
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService
from app.modules.try_on.models import TryOn
from app.modules.try_on.repository import TryOnRepository
from app.modules.try_on.schemas import AvatarTryOnRequest, PhotoTryOnRequest, TryOnJobAcceptedResponse, TryOnSchema
from app.providers.try_on.base import TryOnAvatarParameters, TryOnCoordiItem, TryOnProvider, TryOnProviderRequest
from app.storage.base import StorageService
from app.storage.validators import IMAGE_RULE, validate_file_upload
from app.tasks.job_utils import run_job_with_new_session
from app.utils.datetime import now_kst


DEFAULT_AVATAR = TryOnAvatarParameters(
    height_cm=170.0,
    weight_kg=65.0,
    gender=Gender.NEUTRAL,
)


class TryOnNotFoundError(NotFoundError):
    code = "TRY_ON_NOT_FOUND"
    message = "Try-on 결과를 찾을 수 없습니다."


@dataclass(frozen=True)
class TryOnOwner:
    user_id: uuid.UUID | None
    guest_session_id: uuid.UUID | None

    @classmethod
    def from_principal(cls, principal: Principal) -> "TryOnOwner":
        return cls(user_id=principal.user_id, guest_session_id=principal.guest_session_id)

    @property
    def owner_type(self) -> FileOwnerType:
        return FileOwnerType.USER if self.user_id is not None else FileOwnerType.GUEST

    @property
    def owner_id(self) -> uuid.UUID:
        return self.user_id or self.guest_session_id  # type: ignore[return-value]


class TryOnService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        product_service: ProductService,
        provider: TryOnProvider,
        storage: StorageService,
        try_on_repository: TryOnRepository | None = None,
        guest_repository: GuestRepository | None = None,
        avatar_repository: AvatarRepository | None = None,
        file_repository: FileRepository | None = None,
        saved_coordi_repository: SavedCoordiRepository | None = None,
    ) -> None:
        self.session = session
        self.product_service = product_service
        self.provider = provider
        self.storage = storage
        self.try_ons = try_on_repository or TryOnRepository(session)
        self.guests = guest_repository or GuestRepository(session)
        self.avatars = avatar_repository or AvatarRepository(session)
        self.files = file_repository or FileRepository(session)
        self.saved_coordis = saved_coordi_repository or SavedCoordiRepository(session)
        self.file_service = FileService(session, repository=self.files, storage=storage)
        self.jobs = JobService(session)

    async def enqueue_avatar_try_on(
        self,
        *,
        principal: Principal,
        payload: AvatarTryOnRequest,
        background_tasks: BackgroundTasks,
    ) -> TryOnJobAcceptedResponse:
        self._validate_scope_target(
            scope=payload.scope,
            product_id=payload.product_id,
            saved_coordi_id=payload.saved_coordi_id,
            variant_id=payload.variant_id,
        )
        if payload.scope is TryOnScope.FULL_COORDI and principal.user_id is None:
            raise ForbiddenError("회원만 저장된 코디로 착용해볼 수 있습니다.")
        job = await self.jobs.create_job(principal=principal, job_type=JobType.AVATAR_TRY_ON)
        background_tasks.add_task(
            run_job_with_new_session,
            job_id=job.id,
            runner=self._build_job_runner(
                principal=principal,
                payload=payload,
                source_file_id=None,
            ),
        )
        return TryOnJobAcceptedResponse(jobId=job.id)

    async def enqueue_photo_try_on(
        self,
        *,
        principal: Principal,
        payload: PhotoTryOnRequest,
        photo: UploadFile,
        background_tasks: BackgroundTasks,
    ) -> TryOnJobAcceptedResponse:
        self._validate_scope_target(
            scope=payload.scope,
            product_id=payload.product_id,
            saved_coordi_id=payload.saved_coordi_id,
            variant_id=payload.variant_id,
        )
        if payload.scope is TryOnScope.FULL_COORDI and principal.user_id is None:
            raise ForbiddenError("회원만 저장된 코디로 착용해볼 수 있습니다.")
        owner = TryOnOwner.from_principal(principal)

        guest = None
        if principal.guest_session_id is not None:
            guest = await self.guests.get_by_id(principal.guest_session_id)
            if guest is None:
                raise NotFoundError("게스트 세션을 찾을 수 없습니다.")
            if guest.photo_try_on_count >= settings.guest_photo_limit:
                raise GuestLimitExceededError()

        filename = photo.filename or "try-on-upload.bin"
        content_type = photo.content_type or "application/octet-stream"
        content = await photo.read()
        validate_file_upload(
            filename=filename,
            content_type=content_type,
            content=content,
            rule=IMAGE_RULE,
        )

        source_file = await self.file_service.create_private_file(
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            filename=filename,
            content_type=content_type,
            content=content,
            expires_at=now_kst() + timedelta(minutes=settings.tryon_source_ttl_minutes),
        )

        if guest is not None:
            guest.photo_try_on_count += 1
            await self.session.commit()

        job = await self.jobs.create_job(principal=principal, job_type=JobType.PHOTO_TRY_ON)
        background_tasks.add_task(
            run_job_with_new_session,
            job_id=job.id,
            runner=self._build_job_runner(
                principal=principal,
                payload=payload,
                source_file_id=source_file.id,
            ),
        )
        return TryOnJobAcceptedResponse(jobId=job.id)

    async def get_saved_try_ons(self, *, user_id: uuid.UUID) -> list[TryOnSchema]:
        rows = await self.try_ons.list_saved_by_user(user_id)
        return [TryOnSchema.model_validate(row) for row in rows]

    async def save_try_on(self, *, try_on_id: uuid.UUID, principal: Principal) -> TryOnSchema:
        if principal.user_id is None:
            raise ForbiddenError("회원만 착용 결과를 저장할 수 있습니다.")

        row = await self.try_ons.get_by_id(try_on_id)
        if row is None:
            raise TryOnNotFoundError()
        if row.user_id != principal.user_id:
            raise ForbiddenError("이 착용 결과에 대한 접근 권한이 없습니다.")

        file_metadata = await self.files.get_by_id(row.result_file_id)
        if file_metadata is None:
            raise NotFoundError("결과 파일을 찾을 수 없습니다.")
        if file_metadata.owner_type is not FileOwnerType.USER or file_metadata.owner_id != principal.user_id:
            raise ForbiddenError("이 결과 파일에 대한 접근 권한이 없습니다.")

        row.saved_at = now_kst()
        row.expires_at = None
        file_metadata.expires_at = None
        await self.session.commit()
        await self.session.refresh(row)
        return TryOnSchema.model_validate(row)

    async def delete_saved_try_on(self, *, try_on_id: uuid.UUID, principal: Principal) -> None:
        if principal.user_id is None:
            raise ForbiddenError("회원만 저장된 착용 결과를 삭제할 수 있습니다.")

        row = await self.try_ons.get_by_id(try_on_id)
        if row is None:
            raise TryOnNotFoundError()
        if row.user_id != principal.user_id or row.saved_at is None:
            raise ForbiddenError("이 저장된 착용 결과에 대한 접근 권한이 없습니다.")

        file_metadata = await self.files.get_by_id(row.result_file_id)
        if file_metadata is not None:
            await self.storage.delete(relative_path=file_metadata.path)
            await self.session.delete(file_metadata)
        await self.try_ons.delete(row)
        await self.session.commit()

    def _build_job_runner(
        self,
        *,
        principal: Principal,
        payload: AvatarTryOnRequest | PhotoTryOnRequest,
        source_file_id: uuid.UUID | None,
    ):
        async def runner(session: AsyncSession, _job_service: JobService, job_id: uuid.UUID) -> dict:
            service = self._spawn_with_session(session)
            owner = TryOnOwner.from_principal(principal)
            source_path: str | None = None

            if source_file_id is not None:
                source_file = await service.files.get_by_id(source_file_id)
                if source_file is None:
                    raise NotFoundError("원본 사진을 찾을 수 없습니다.")
                if not hasattr(service.storage, "resolve_path"):
                    raise GenerationFailedError("저장소 경로를 확인할 수 없습니다.")
                source_path = str(service.storage.resolve_path(source_file.path))  # type: ignore[attr-defined]

            provider_request = await service._build_provider_request(
                principal=principal,
                scope=payload.scope,
                product_id=payload.product_id,
                saved_coordi_id=payload.saved_coordi_id,
                variant_id=payload.variant_id,
                height_cm=payload.height_cm,
                weight_kg=payload.weight_kg,
                gender=payload.gender,
                source_image_path=source_path,
                simulate_failure=payload.simulate_failure,
            )
            result = await service.provider.generate(provider_request)
            stored = await service.file_service.create_private_file(
                owner_type=owner.owner_type,
                owner_id=owner.owner_id,
                filename=result.filename,
                content_type=result.content_type,
                content=result.content,
                expires_at=now_kst() + timedelta(minutes=settings.tryon_result_ttl_minutes),
            )

            row = TryOn(
                user_id=owner.user_id,
                guest_session_id=owner.guest_session_id,
                job_id=job_id,
                scope=payload.scope,
                product_id=payload.product_id,
                saved_coordi_id=payload.saved_coordi_id,
                result_file_id=stored.id,
                provider=TryOnProviderKind.MOCK,
                request_json=self._request_json(payload, source_file_id=source_file_id),
                saved_at=None,
                expires_at=stored.expires_at,
            )
            await service.try_ons.add(row)
            await session.commit()
            return {
                "tryOnId": str(row.id),
                "resultFileId": str(stored.id),
                "expiresAt": row.expires_at.isoformat() if row.expires_at else None,
            }

        return runner

    def _spawn_with_session(self, session: AsyncSession) -> "TryOnService":
        return TryOnService(
            session,
            product_service=ProductService(ProductRepository(session)),
            provider=self.provider,
            storage=self.storage,
            saved_coordi_repository=SavedCoordiRepository(session),
        )

    async def _build_provider_request(
        self,
        *,
        principal: Principal,
        scope: TryOnScope,
        product_id: uuid.UUID | None,
        saved_coordi_id: uuid.UUID | None,
        variant_id: uuid.UUID | None,
        height_cm: float | None,
        weight_kg: float | None,
        gender: Gender | None,
        source_image_path: str | None,
        simulate_failure: bool,
    ) -> TryOnProviderRequest:
        product = None
        coordi_items: list[TryOnCoordiItem] = []
        if scope is TryOnScope.PRODUCT_ONLY:
            if product_id is None:
                raise ValidationError("productOnly 범위에서는 productId가 필요합니다.")
            product = await self.product_service.get_product(product_id)
            if variant_id is not None:
                variants = await self.product_service.get_available_variants(product_id)
                if not any(item.variant_id == variant_id for item in variants):
                    raise NotFoundError("옵션(variant)을 찾을 수 없습니다.")
        else:
            if saved_coordi_id is None:
                raise ValidationError("fullCoordi 범위에서는 savedCoordiId가 필요합니다.")
            coordi_service = SavedCoordiService(self.saved_coordis, product_service=self.product_service)
            item_details = await coordi_service.get_owned_items_for_try_on(
                saved_coordi_id=saved_coordi_id,
                user_id=principal.user_id,
            )
            coordi_items = [
                TryOnCoordiItem(
                    product=await self.product_service.get_product(item.product_id),
                    variant=item.variant,
                )
                for item in item_details
            ]

        avatar = await self._resolve_avatar_parameters(
            principal=principal,
            height_cm=height_cm,
            weight_kg=weight_kg,
            gender=gender,
        )
        return TryOnProviderRequest(
            scope=scope,
            avatar=avatar,
            product=product,
            variant_id=variant_id,
            coordi_items=coordi_items,
            source_image_path=source_image_path,
            simulate_failure=simulate_failure,
        )

    async def _resolve_avatar_parameters(
        self,
        *,
        principal: Principal,
        height_cm: float | None,
        weight_kg: float | None,
        gender: Gender | None,
    ) -> TryOnAvatarParameters:
        if principal.user_id is not None:
            avatar = await self.avatars.get_by_user_id(principal.user_id)
            if avatar is not None:
                base = TryOnAvatarParameters(
                    height_cm=float(avatar.height_cm),
                    weight_kg=float(avatar.weight_kg),
                    gender=avatar.gender,
                )
            else:
                base = DEFAULT_AVATAR
        else:
            guest = await self.guests.get_by_id(principal.guest_session_id)
            if guest is not None and guest.height_cm is not None and guest.weight_kg is not None and guest.gender is not None:
                base = TryOnAvatarParameters(
                    height_cm=float(guest.height_cm),
                    weight_kg=float(guest.weight_kg),
                    gender=guest.gender,
                )
            else:
                base = DEFAULT_AVATAR

        return TryOnAvatarParameters(
            height_cm=height_cm if height_cm is not None else base.height_cm,
            weight_kg=weight_kg if weight_kg is not None else base.weight_kg,
            gender=gender if gender is not None else base.gender,
        )

    @staticmethod
    def _validate_scope_target(
        *,
        scope: TryOnScope,
        product_id: uuid.UUID | None,
        saved_coordi_id: uuid.UUID | None,
        variant_id: uuid.UUID | None,
    ) -> None:
        if scope is TryOnScope.PRODUCT_ONLY:
            if product_id is None:
                raise ValidationError("productId is required for productOnly scope.")
            if saved_coordi_id is not None:
                raise ValidationError("savedCoordiId is not allowed for productOnly scope.")
            return
        if saved_coordi_id is None:
            raise ValidationError("savedCoordiId is required for fullCoordi scope.")
        if product_id is not None or variant_id is not None:
            raise ValidationError("productId and variantId are not allowed for fullCoordi scope.")

    @staticmethod
    def _request_json(
        payload: AvatarTryOnRequest | PhotoTryOnRequest,
        *,
        source_file_id: uuid.UUID | None = None,
    ) -> dict:
        data = payload.model_dump(mode="json", by_alias=True, exclude_none=True)
        if source_file_id is not None:
            data["sourceFileId"] = str(source_file_id)
        return data
