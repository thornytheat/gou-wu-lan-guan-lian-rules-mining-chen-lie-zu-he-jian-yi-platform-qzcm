"""认证相关模型。"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class LoginResponse(BaseModel):
    access_token: str
    token: str
    token_type: str = "bearer"
    user: dict


class MeResponse(BaseModel):
    user: dict
