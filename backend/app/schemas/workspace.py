from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel, UserOut


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    timezone: str = Field(default="UTC", max_length=80)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=80)
    version: int


class WorkspaceOut(ApiModel):
    id: str
    name: str
    slug: str
    description: str
    icon: str | None
    timezone: str
    is_archived: bool
    version: int
    role: str | None = None
    created_at: datetime


class MemberOut(ApiModel):
    id: str
    role: str
    joined_at: datetime
    user: UserOut


class InviteCreate(BaseModel):
    email: str | None = None
    role: str = "viewer"
    expires_in_hours: int = Field(default=72, ge=1, le=720)
    max_uses: int = Field(default=1, ge=1, le=100)


class InviteOut(BaseModel):
    id: str
    token: str
    invite_url: str
    expires_at: datetime


class RoleUpdate(BaseModel):
    role: str


class OwnershipTransfer(BaseModel):
    user_id: str
