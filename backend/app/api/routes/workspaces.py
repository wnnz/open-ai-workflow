from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.security import invitation_token, token_hash
from app.models.entities import Workspace, WorkspaceInvitation, WorkspaceMember, WorkspaceRole
from app.schemas.common import MessageOut
from app.schemas.workspace import (
    InviteCreate,
    InviteOut,
    MemberOut,
    OwnershipTransfer,
    RoleUpdate,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from app.services.workspaces import audit, ensure_invitation_active, require_role, slugify

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(db: DbSession, user: CurrentUser) -> list[WorkspaceOut]:
    rows = (
        await db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user.id, Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at)
        )
    ).all()
    return [
        WorkspaceOut.model_validate(workspace).model_copy(update={"role": role})
        for workspace, role in rows
    ]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, db: DbSession, user: CurrentUser) -> Workspace:
    workspace = Workspace(
        name=payload.name.strip(),
        slug=slugify(payload.name),
        description=payload.description,
        timezone=payload.timezone,
    )
    db.add(workspace)
    await db.flush()
    db.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner.value)
    )
    db.add(audit(workspace.id, user.id, "workspace.created", "workspace", workspace.id))
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: str, payload: WorkspaceUpdate, db: DbSession, user: CurrentUser
) -> Workspace:
    await require_role(db, workspace_id, user.id, "admin")
    workspace = await db.get(Workspace, workspace_id)
    if workspace.version != payload.version:
        raise HTTPException(status.HTTP_409_CONFLICT, "Workspace was updated by another member")
    for field in ("name", "description", "icon", "timezone"):
        value = getattr(payload, field)
        if value is not None:
            setattr(workspace, field, value)
    workspace.version += 1
    db.add(audit(workspace_id, user.id, "workspace.updated", "workspace", workspace_id))
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.post("/{workspace_id}/archive", response_model=WorkspaceOut)
async def archive_workspace(workspace_id: str, db: DbSession, user: CurrentUser) -> Workspace:
    await require_role(db, workspace_id, user.id, "owner")
    workspace = await db.get(Workspace, workspace_id)
    workspace.is_archived = True
    db.add(audit(workspace_id, user.id, "workspace.archived", "workspace", workspace_id))
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.post("/{workspace_id}/restore", response_model=WorkspaceOut)
async def restore_workspace(workspace_id: str, db: DbSession, user: CurrentUser) -> Workspace:
    await require_role(db, workspace_id, user.id, "owner")
    workspace = await db.get(Workspace, workspace_id)
    workspace.is_archived = False
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}", response_model=MessageOut)
async def delete_workspace(workspace_id: str, db: DbSession, user: CurrentUser) -> MessageOut:
    await require_role(db, workspace_id, user.id, "owner")
    workspace = await db.get(Workspace, workspace_id)
    workspace.deleted_at = datetime.now(UTC)
    db.add(audit(workspace_id, user.id, "workspace.deleted", "workspace", workspace_id))
    await db.commit()
    return MessageOut(message="Workspace scheduled for deletion")


@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(
    workspace_id: str, db: DbSession, user: CurrentUser
) -> list[WorkspaceMember]:
    await require_role(db, workspace_id, user.id)
    return list(
        (
            await db.scalars(
                select(WorkspaceMember)
                .options(selectinload(WorkspaceMember.user))
                .where(WorkspaceMember.workspace_id == workspace_id)
                .order_by(WorkspaceMember.joined_at)
            )
        ).all()
    )


@router.post(
    "/{workspace_id}/invitations", response_model=InviteOut, status_code=status.HTTP_201_CREATED
)
async def create_invitation(
    workspace_id: str, payload: InviteCreate, request: Request, db: DbSession, user: CurrentUser
) -> InviteOut:
    await require_role(db, workspace_id, user.id, "admin")
    if payload.role not in {"admin", "editor", "viewer"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid invitation role")
    raw, digest = invitation_token()
    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=payload.email.strip().lower() if payload.email else None,
        token_hash=digest,
        role=payload.role,
        expires_at=datetime.now(UTC) + timedelta(hours=payload.expires_in_hours),
        max_uses=payload.max_uses,
        created_by=user.id,
    )
    db.add(invitation)
    await db.flush()
    db.add(audit(workspace_id, user.id, "invitation.created", "invitation", invitation.id))
    await db.commit()
    return InviteOut(
        id=invitation.id,
        token=raw,
        invite_url=f"{str(request.base_url).rstrip('/')}/invite/{raw}",
        expires_at=invitation.expires_at,
    )


@router.post("/invitations/{raw_token}/accept", response_model=WorkspaceOut)
async def accept_invitation(raw_token: str, db: DbSession, user: CurrentUser) -> Workspace:
    invitation = await db.scalar(
        select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == token_hash(raw_token))
    )
    if not invitation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    ensure_invitation_active(invitation)
    if invitation.email and invitation.email != user.email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invitation belongs to another email")
    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == invitation.workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if not existing:
        db.add(
            WorkspaceMember(
                workspace_id=invitation.workspace_id, user_id=user.id, role=invitation.role
            )
        )
    invitation.use_count += 1
    db.add(
        audit(invitation.workspace_id, user.id, "invitation.accepted", "invitation", invitation.id)
    )
    await db.commit()
    return await db.get(Workspace, invitation.workspace_id)


@router.patch("/{workspace_id}/members/{member_id}", response_model=MemberOut)
async def update_member_role(
    workspace_id: str, member_id: str, payload: RoleUpdate, db: DbSession, user: CurrentUser
) -> WorkspaceMember:
    await require_role(db, workspace_id, user.id, "admin")
    member = await db.get(WorkspaceMember, member_id)
    if not member or member.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if member.role == "owner" or payload.role not in {"admin", "editor", "viewer"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Owner role must be transferred")
    member.role = payload.role
    db.add(
        audit(
            workspace_id,
            user.id,
            "member.role_changed",
            "member",
            member.id,
            {"role": payload.role},
        )
    )
    await db.commit()
    await db.refresh(member, ["user"])
    return member


@router.delete("/{workspace_id}/members/{member_id}", response_model=MessageOut)
async def remove_member(
    workspace_id: str, member_id: str, db: DbSession, user: CurrentUser
) -> MessageOut:
    actor = await require_role(db, workspace_id, user.id)
    member = await db.get(WorkspaceMember, member_id)
    if not member or member.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if member.role == "owner":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Owner must transfer ownership")
    if member.user_id != user.id and actor.role not in {"owner", "admin"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient workspace role")
    await db.delete(member)
    db.add(audit(workspace_id, user.id, "member.removed", "member", member_id))
    await db.commit()
    return MessageOut(message="Member removed")


@router.post("/{workspace_id}/transfer", response_model=MessageOut)
async def transfer_ownership(
    workspace_id: str, payload: OwnershipTransfer, db: DbSession, user: CurrentUser
) -> MessageOut:
    current = await require_role(db, workspace_id, user.id, "owner")
    target = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == payload.user_id
        )
    )
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target member not found")
    current.role = "admin"
    target.role = "owner"
    db.add(audit(workspace_id, user.id, "workspace.ownership_transferred", "member", target.id))
    await db.commit()
    return MessageOut(message="Ownership transferred")
