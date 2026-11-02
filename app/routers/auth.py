from bcrypt import hashpw, gensalt, checkpw
from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, Token

DUMMY_HASH = hashpw(b"dummy_password", gensalt())
router = APIRouter()


@router.post("/signup", response_model=UserRead, status_code=201)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    hashed = hashpw(user.password.encode('utf-8'), gensalt()).decode('utf-8')
    new_user = User(email=user.email.lower(), password_hash=hashed)
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(func.lower(User.email) == user.email.lower()))
    user_db = result.scalar_one_or_none()
    if user_db is None:
        checkpw(user.password.encode('utf-8'), DUMMY_HASH)
        raise HTTPException(status_code=401, detail="No such user or incorrect password")
    if not checkpw(user.password.encode('utf-8'), user_db.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="No such user or incorrect password")
    token = create_access_token(user_db.id)
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
