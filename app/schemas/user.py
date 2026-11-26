from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(examples=["Password123!"])

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[^\w\s]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserRoleUpdate(BaseModel):
    role: Literal["customer", "admin"]
