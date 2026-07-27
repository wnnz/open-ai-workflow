from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class ScriptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    description: str = Field(default="", max_length=4000)
    tags: list[str] = []
    source_code: str = Field(min_length=1, max_length=1_000_000)
    entrypoint: str = "main"
    input_schema: dict[str, Any] = {"type": "object"}
    output_schema: dict[str, Any] = {}
    change_note: str = "Initial version"


class ScriptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = None
    source_code: str = Field(min_length=1, max_length=1_000_000)
    entrypoint: str = "main"
    input_schema: dict[str, Any] = {"type": "object"}
    output_schema: dict[str, Any] = {}
    change_note: str = "Updated script"
    expected_version: int


class ScriptOut(ApiModel):
    id: str
    workspace_id: str
    name: str
    slug: str
    description: str
    tags: list[str]
    latest_version: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class ScriptVersionOut(ApiModel):
    id: str
    script_id: str
    version: int
    source_type: str
    source_code: str
    entrypoint: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    content_hash: str
    change_note: str
    created_by: str
    created_at: datetime


class ScriptTestIn(BaseModel):
    version: int | None = None
    inputs: dict[str, Any] = {}
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class ScriptTestOut(BaseModel):
    status: str
    outputs: dict[str, Any] = {}
    logs: list[str] = []
    error: str | None = None
    elapsed_ms: int
