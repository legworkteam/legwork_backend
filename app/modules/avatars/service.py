from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.avatars.models import Avatar
from app.modules.avatars.repository import AvatarRepository
from app.modules.avatars.schemas import AvatarParametersPayload, AvatarSchema, GuestAvatarParametersSchema
from app.modules.guests.repository import GuestRepository


class AvatarAlreadyExistsError(ConflictError):
    code = "AVATAR_ALREADY_EXISTS"
    message = "Avatar already exists for this member."


class AvatarNotFoundError(NotFoundError):
    code = "AVATAR_NOT_FOUND"
    message = "Avatar not found."


class AvatarService:
    def __init__(
        self,
        repository: AvatarRepository,
        *,
        guest_repository: GuestRepository | None = None,
    ) -> None:
        self.repository = repository
        self.session = repository.session
        self.guest_repository = guest_repository or GuestRepository(repository.session)

    async def create_member_avatar(
        self,
        *,
        user_id: uuid.UUID,
        payload: AvatarParametersPayload,
    ) -> AvatarSchema:
        existing = await self.repository.get_by_user_id(user_id)
        if existing is not None:
            raise AvatarAlreadyExistsError()

        avatar = Avatar(
            user_id=user_id,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            gender=payload.gender,
            preview_file_id=None,
        )
        await self.repository.add(avatar)
        await self.session.commit()
        return AvatarSchema.model_validate(avatar)

    async def get_member_avatar(self, *, user_id: uuid.UUID) -> AvatarSchema:
        avatar = await self.repository.get_by_user_id(user_id)
        if avatar is None:
            raise AvatarNotFoundError()
        return AvatarSchema.model_validate(avatar)

    async def upsert_member_avatar(
        self,
        *,
        user_id: uuid.UUID,
        payload: AvatarParametersPayload,
    ) -> AvatarSchema:
        avatar = await self.repository.get_by_user_id(user_id)
        if avatar is None:
            avatar = Avatar(
                user_id=user_id,
                height_cm=payload.height_cm,
                weight_kg=payload.weight_kg,
                gender=payload.gender,
                preview_file_id=None,
            )
            await self.repository.add(avatar)
        else:
            avatar.height_cm = payload.height_cm
            avatar.weight_kg = payload.weight_kg
            avatar.gender = payload.gender
        await self.session.commit()
        await self.session.refresh(avatar)
        return AvatarSchema.model_validate(avatar)

    async def update_guest_avatar_parameters(
        self,
        *,
        guest_session_id: uuid.UUID,
        payload: AvatarParametersPayload,
    ) -> GuestAvatarParametersSchema:
        guest = await self.guest_repository.get_by_id(guest_session_id)
        if guest is None:
            raise AvatarNotFoundError("Guest session not found.")
        guest.height_cm = payload.height_cm
        guest.weight_kg = payload.weight_kg
        guest.gender = payload.gender
        await self.session.commit()
        return GuestAvatarParametersSchema(
            heightCm=float(guest.height_cm),
            weightKg=float(guest.weight_kg),
            gender=guest.gender,
        )
