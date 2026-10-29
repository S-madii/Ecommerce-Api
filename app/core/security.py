from datetime import datetime, timezone, timedelta

import jwt

from app.core.config import settings


def create_access_token(user_id: int):
    iat = datetime.now(timezone.utc)
    exp = iat + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")
