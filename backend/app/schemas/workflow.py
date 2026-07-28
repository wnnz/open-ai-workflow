from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = None
    description: str = ""
    app_type: str = "workflow"


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    graph: dict[str, Any]
    expected_version: int


class WorkflowEnvironmentVariableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value_type: str = Field(default="string", pattern="^(string|number|secret)$")
    value: str = Field(default="", max_length=20000)
    description: str = Field(default="", max_length=500)


class WorkflowEnvironmentVariableUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value_type: str = Field(default="string", pattern="^(string|number|secret)$")
    value: str | None = Field(default=None, max_length=20000)
    description: str = Field(default="", max_length=500)


class WorkflowEnvironmentVariableOut(ApiModel):
    id: str
    name: str
    value_type: str
    value: str
    has_value: bool
    description: str
    created_at: datetime
    updated_at: datetime


class WorkflowOut(ApiModel):
    id: str
    workspace_id: str
    name: str
    slug: str
    description: str
    app_type: str
    draft_graph: dict[str, Any]
    draft_version: int
    published_version_id: str | None
    published_access: str
    created_at: datetime
    updated_at: datetime


class PublishIn(BaseModel):
    change_note: str = "Published update"
    access: str = Field(default="public", pattern="^(public|protected)$")


class WorkflowVersionOut(ApiModel):
    id: str
    version: int
    graph: dict[str, Any]
    resolved_references: dict[str, Any]
    change_note: str
    created_at: datetime


class RunIn(BaseModel):
    inputs: dict[str, Any] = {}
    user: str = Field(default="", max_length=255)


class RunOut(ApiModel):
    id: str
    status: str
    triggered_by: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    trace: list[dict[str, Any]]
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class RunSummaryOut(ApiModel):
    id: str
    status: str
    triggered_by: str
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class RunPage(BaseModel):
    items: list[RunSummaryOut]
    total: int
    limit: int
    offset: int


class ApprovalResponseIn(BaseModel):
    action_id: str = Field(min_length=1, max_length=64)
    data: dict[str, Any] = {}
    comment: str = Field(default="", max_length=4000)


class ApprovalOut(ApiModel):
    id: str
    run_id: str
    node_id: str
    status: str
    request: dict[str, Any]
    response: dict[str, Any]
    expires_at: datetime | None
    created_at: datetime
    responded_at: datetime | None
