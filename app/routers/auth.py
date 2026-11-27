import asyncio

from bcrypt import checkpw, gensalt, hashpw
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    bearer_scheme,
    create_access_token,
    create_refresh_token,
    decode_and_verify_token,
    get_current_user,
    rate_limit_auth,
    require_admin,
    revoke_token_payload,
)
from app.db import get_db
from app.models import User
from app.schemas import RefreshTokenRequest, Token, UserCreate, UserRead, UserRoleUpdate, UserList

DUMMY_HASH = hashpw(b"dummy_password", gensalt())
router = APIRouter()


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    hashed = (await asyncio.to_thread(hashpw, user.password.encode("utf-8"), gensalt())).decode("utf-8")
    normalized_email = user.email.lower()
    role = (
        "admin"
        if settings.ADMIN_EMAIL and normalized_email == settings.ADMIN_EMAIL.lower()
        else "customer"
    )
    new_user = User(email=normalized_email, password_hash=hashed, role=role)
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    await db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(rate_limit_auth)],
)
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(func.lower(User.email) == user.email.lower()))
    user_db = result.scalar_one_or_none()
    if user_db is None:
        await asyncio.to_thread(checkpw, user.password.encode("utf-8"), DUMMY_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No such user or incorrect password")
    is_valid = await asyncio.to_thread(checkpw, user.password.encode("utf-8"), user_db.password_hash.encode("utf-8"))
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No such user or incorrect password")
    return Token(
        access_token=create_access_token(user_db.id),
        refresh_token=create_refresh_token(user_db.id),
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = await decode_and_verify_token(body.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError()
    user_db = await db.get(User, int(user_id))
    if user_db is None:
        raise UnauthorizedError()
    await revoke_token_payload(payload)
    return Token(
        access_token=create_access_token(user_db.id),
        refresh_token=create_refresh_token(user_db.id),
        token_type="bearer",
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    payload = await decode_and_verify_token(credentials.credentials, expected_type="access")
    await revoke_token_payload(payload)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=UserList)
async def list_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    role: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    conditions = []
    if role:
        conditions.append(User.role == role)
    if q:
        conditions.append(User.email.icontains(q, autoescape=True))

    count_stmt = select(func.count()).select_from(User).where(*conditions)
    total = await db.scalar(count_stmt) or 0

    query = (
        select(User)
        .where(*conditions)
        .order_by(User.id.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    users = result.scalars().all()
    return UserList(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )



@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = await db.get(User, user_id)
    if not target_user:
        raise NotFoundError("User not found")
    target_user.role = role_in.role
    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = await db.get(User, user_id)
    if not target_user:
        raise NotFoundError("User not found")
    if target_user.id == current_admin.id:
        raise ConflictError("Cannot delete your own admin account")
    await db.delete(target_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Cannot delete user with existing orders")
    return None
