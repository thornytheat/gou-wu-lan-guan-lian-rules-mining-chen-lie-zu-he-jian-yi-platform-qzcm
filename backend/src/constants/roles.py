"""RBAC 角色常量。

前后端必须一致：users.role / src/constants/roles.py / frontend/src/constants/roles.ts。
角色：admin 品类总监｜analyst 品类运营｜viewer 店长（只读本店建议）。
"""
from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"

ALL_ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER)

# 能力矩阵：action -> 允许的角色
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "baskets:read": (ROLE_ADMIN, ROLE_ANALYST),
    "baskets:import": (ROLE_ADMIN, ROLE_ANALYST),
    "mining:read": ALL_ROLES,
    "mining:run": (ROLE_ADMIN, ROLE_ANALYST),
    "rules:read": ALL_ROLES,
    "rules:review": (ROLE_ADMIN, ROLE_ANALYST),
    "rules:publish": (ROLE_ADMIN,),
    "planogram:read": ALL_ROLES,
    "planogram:write": (ROLE_ADMIN, ROLE_ANALYST),
    "planogram:publish": (ROLE_ADMIN,),
    "rules:export": (ROLE_ADMIN, ROLE_ANALYST),
    "audit:read": (ROLE_ADMIN,),
}

ROLE_LABELS: dict[str, str] = {
    ROLE_ADMIN: "品类总监",
    ROLE_ANALYST: "品类运营",
    ROLE_VIEWER: "店长（只读）",
}


def role_can(role: str, action: str) -> bool:
    return role in PERMISSIONS.get(action, ())


def role_permissions(role: str) -> list[str]:
    return [action for action, roles in PERMISSIONS.items() if role in roles]
