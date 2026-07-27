import re
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditEvent, Workspace, WorkspaceMember, WorkspaceRole

ROLE_WEIGHT = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "workspace"
    return f"{slug}-{secrets.token_hex(3)}"


async def membership(db: AsyncSession, workspace_id: str, user_id: str) -> WorkspaceMember:
    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
        )
    )
    workspace = await db.get(Workspace, workspace_id)
    if not member or not workspace or workspace.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return member


async def require_role(
    db: AsyncSession, workspace_id: str, user_id: str, minimum: str = WorkspaceRole.viewer.value
) -> WorkspaceMember:
    member = await membership(db, workspace_id, user_id)
    if ROLE_WEIGHT.get(member.role, 0) < ROLE_WEIGHT[minimum]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient workspace permission")
    return member


def audit(
    workspace_id: str,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str | None,
    detail: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )


def ensure_invitation_active(invitation) -> None:
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        invitation.revoked_at is not None
        or expires_at < datetime.now(UTC)
        or invitation.use_count >= invitation.max_uses
    ):
        raise HTTPException(status.HTTP_410_GONE, "Invitation expired or revoked")
