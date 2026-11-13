"""登录 / 当前用户。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.auth import LoginRequest
from src.services import auth_service


def login(db: Session, payload: LoginRequest) -> dict:
    user, token = auth_service.authenticate(db, payload.email, payload.password)
    return {
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "user": auth_service.serialize(user),
    }


def me(user: User) -> dict:
    return {"user": auth_service.serialize(user)}
