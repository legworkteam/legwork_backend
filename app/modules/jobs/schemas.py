from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import JobStatus, JobType


class JobSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(alias="jobId")
    type: JobType
    status: JobStatus
    progress: int
    result_json: dict | None = Field(alias="result")
    error_json: dict | None = Field(alias="error")
    expires_at: datetime = Field(alias="expiresAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
