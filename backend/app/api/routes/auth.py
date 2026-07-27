from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, text

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User, Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.common import LoginIn, RegisterIn, TokenOut, UserOut
from app.services.workspaces import slugify

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: DbSession) -> TokenOut:
    email = payload.email.strip().lower()
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(73920418)"))
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    is_first_user = (await db.scalar(select(func.count(User.id))) or 0) == 0
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        is_platform_admin=is_first_user,
    )
    db.add(user)
    await db.flush()
    workspace = Workspace(name=f"{user.display_name}'s Workspace", slug=slugify(user.display_name))
    db.add(workspace)
    await db.flush()
    db.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner.value)
    )
    await db.commit()
    await db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: DbSession) -> TokenOut:
    user = await db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is disabled")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
