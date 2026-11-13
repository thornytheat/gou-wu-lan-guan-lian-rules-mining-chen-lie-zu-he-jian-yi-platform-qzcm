"""登录与身份读取。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.log_templates import ACTION_LOGIN
from src.constants.roles import role_permissions
from src.models.user import User
from src.services import audit_service
from src.utils.errors import AppError
from src.utils.jwt import create_access_token
from src.utils.password import verify_password


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    normalized = (email or "").strip().lower()
    user = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(codes.AUTH_INVALID, "邮箱或密码不正确", f"email={normalized}")
    if not user.is_active:
        raise AppError(codes.AUTH_INVALID, "账号已停用", f"email={normalized}")
    token = create_access_token(str(user.id), user.role, user.email)
    audit_service.record(db, action=ACTION_LOGIN, actor=user, entity_type="user", entity_id=user.id)
    db.commit()
    return user, token


def serialize(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "permissions": role_permissions(user.role),
        "is_active": user.is_active,
    }
