"""Guest session business rules.

Creates a guest session (optionally within a QR-provided Store/Campaign
context), issues a guest JWT, and sets expiry to 23:59:59 KST of the day.
"""

from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import create_guest_token
from app.modules.guests.repository import GuestRepository
from app.modules.guests.schemas import (
    CampaignContext,
    GuestSessionCreateRequest,
    GuestSessionResponse,
    StoreContext,
)
from app.utils.datetime import end_of_day_kst, now_kst


class QrInvalidError(NotFoundError):
    code = "QR_INVALID"
    message = "유효하지 않은 QR 코드입니다."


class QrExpiredError(ValidationError):
    code = "QR_EXPIRED"
    message = "만료된 QR 코드입니다."


class GuestService:
    def __init__(self, repository: GuestRepository) -> None:
        self.repository = repository

    async def create_session(
        self, payload: GuestSessionCreateRequest
    ) -> GuestSessionResponse:
        store_ctx: StoreContext | None = None
        campaign_ctx: CampaignContext | None = None
        qr_code_id = None

        if payload.qr_code:
            mapping = await self.repository.get_qr_mapping(payload.qr_code)
            if mapping is None or not mapping.active:
                raise QrInvalidError()
            if mapping.expires_at is not None and mapping.expires_at <= now_kst():
                raise QrExpiredError()

            qr_code_id = mapping.id
            if mapping.store_id is not None:
                store = await self.repository.get_store(mapping.store_id)
                if store is not None:
                    store_ctx = StoreContext(storeId=store.id, name=store.name)
            if mapping.campaign_id is not None:
                campaign = await self.repository.get_campaign(mapping.campaign_id)
                if campaign is not None:
                    campaign_ctx = CampaignContext(
                        campaignId=campaign.id, name=campaign.name
                    )

        expires_at = end_of_day_kst()
        session = await self.repository.create_session(
            qr_code_id=qr_code_id, expires_at=expires_at
        )
        guest_token = create_guest_token(str(session.id), expires_at)

        return GuestSessionResponse(
            guestToken=guest_token,
            guestSessionId=session.id,
            store=store_ctx,
            campaign=campaign_ctx,
            expiresAt=expires_at,
        )
