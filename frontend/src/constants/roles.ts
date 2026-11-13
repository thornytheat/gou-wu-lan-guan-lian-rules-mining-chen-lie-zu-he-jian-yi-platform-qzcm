/** 角色与能力矩阵（镜像 backend/src/constants/roles.py）。 */
export const ROLES = ['admin', 'analyst', 'viewer'] as const
export type Role = (typeof ROLES)[number]

export const ROLE_LABELS: Record<Role, string> = {
  admin: '品类总监',
  analyst: '品类运营',
  viewer: '店长（只读）',
}

export const ROLE_TASKS: Record<Role, string> = {
  admin: '补传入库、参数、审核、发布',
  analyst: '补传入库、跑挖掘、筛规则、提建议',
  viewer: '只看已发布陈列建议',
}
