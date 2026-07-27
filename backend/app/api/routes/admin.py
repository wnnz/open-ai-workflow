from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, text

from app.api.deps import CurrentUser, DbSession
from app.models.entities import User
from app.schemas.admin import AdminUserUpdate
from app.schemas.common import UserOut

router = APIRouter(prefix="/admin/users", tags=["platform administration"])


def require_platform_admin(user: User) -> None:
    if not user.is_platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform administrator required")


async def lock_admin_changes(db: DbSession) -> None:
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(73920419)"))


@router.get("", response_model=list[UserOut])
async def list_users(db: DbSession, user: CurrentUser) -> list[User]:
    require_platform_admin(user)
    return list((await db.scalars(select(User).order_by(User.created_at.asc()))).all())


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str, payload: AdminUserUpdate, db: DbSession, user: CurrentUser
) -> User:
    require_platform_admin(user)
    await lock_admin_changes(db)
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    removes_active_admin = target.is_platform_admin and (
        payload.is_platform_admin is False or payload.is_active is False
    )
    if removes_active_admin:
        active_admins = await db.scalar(
            select(func.count(User.id)).where(
                User.is_platform_admin.is_(True), User.is_active.is_(True)
            )
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "The last active administrator cannot be removed"
            )
    if target.id == user.id and payload.is_active is False:
        raise HTTPException(status.HTTP_409_CONFLICT, "Administrators cannot disable themselves")

    if payload.is_platform_admin is not None:
        target.is_platform_admin = payload.is_platform_admin
    if payload.is_active is not None:
        target.is_active = payload.is_active
    await db.commit()
    await db.refresh(target)
    return target
