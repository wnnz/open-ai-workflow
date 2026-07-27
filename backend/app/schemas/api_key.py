from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workflow_id: str | None = None


class ApiKeyOut(ApiModel):
    id: str
    workspace_id: str
    workflow_id: str | None
    name: str
    key_prefix: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    key: str
