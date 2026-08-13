"""Guest session request/response schemas (camelCase JSON)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GuestSessionCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    qr_code: str | None = Field(default=None, alias="qrCode")


class StoreContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    store_id: uuid.UUID = Field(alias="storeId")
    name: str


class CampaignContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    campaign_id: uuid.UUID = Field(alias="campaignId")
    name: str


class GuestSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    guest_token: str = Field(alias="guestToken")
    guest_session_id: uuid.UUID = Field(alias="guestSessionId")
    store: StoreContext | None = None
    campaign: CampaignContext | None = None
    expires_at: datetime = Field(alias="expiresAt")
