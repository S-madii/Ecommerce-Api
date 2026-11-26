from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import redis_client
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer()


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


async def revoke_token_payload(payload: dict[str, Any]) -> None:
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = max(int(exp) - now_ts, 1)
    try:
        await redis_client.set(f"revoked:jwt:{jti}", "1", ex=ttl)
    except RedisError:
        pass


async def is_token_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    try:
        return await redis_client.get(f"revoked:jwt:{jti}") is not None
    except RedisError:
        return False


async def decode_and_verify_token(raw_token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(
            raw_token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedError()

    token_type = payload.get("type", "access")
    if token_type != expected_type:
        raise UnauthorizedError()

    if await is_token_revoked(payload.get("jti")):
        raise UnauthorizedError("Token has been revoked")

    return payload


async def rate_limit_auth(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:auth:{client_ip}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 60)
        if count > settings.AUTH_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts, please try again later",
            )
    except RedisError:
        pass


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = await decode_and_verify_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError()
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError()
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise ForbiddenError("Admin privileges required")
    return current_user
