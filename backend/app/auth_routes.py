from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.models import LoginIn, RegisterIn, TokenOut, UserOut, utcnow
from app.security import CurrentUser, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
async def register(payload: RegisterIn):
    db = get_db()
    if await db.users.find_one({"username": payload.username}):
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = {
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "display_name": payload.display_name or payload.username,
        "created_at": utcnow(),
    }
    await db.users.insert_one(user)
    return TokenOut(
        access_token=create_token(user["username"]),
        user=UserOut(username=user["username"], display_name=user["display_name"]),
    )


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn):
    db = get_db()
    user = await db.users.find_one({"username": payload.username})
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenOut(
        access_token=create_token(user["username"]),
        user=UserOut(username=user["username"], display_name=user["display_name"]),
    )


@router.get("/me", response_model=UserOut)
async def me(username: str = CurrentUser):
    db = get_db()
    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserOut(username=user["username"], display_name=user["display_name"])
