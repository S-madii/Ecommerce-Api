from datetime import datetime, timezone, timedelta

import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.models import User


def create_access_token(user_id: int):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                           db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise UnauthorizedError()
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError()
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError()
    return user
