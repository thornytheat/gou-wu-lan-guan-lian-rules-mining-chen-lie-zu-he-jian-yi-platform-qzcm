/**
 * 共享枚举（前端镜像；后端定义在 backend/src/constants/enums.py）。
 * 两份必须一致；README「枚举出现位置」列出全部落点。
 */
export const STORE_TIERS = ['high', 'mid', 'low'] as const
export const RUN_STATUSES = ['queued', 'running', 'succeeded', 'failed'] as const
export const RULE_STATUSES = ['candidate', 'adopted', 'rejected', 'parked'] as const
export const REVIEW_DECISIONS = ['adopt', 'reject', 'park'] as const
export const SLOT_STATUSES = ['draft', 'published', 'archived'] as const

export type StoreTier = (typeof STORE_TIERS)[number]
export type RunStatus = (typeof RUN_STATUSES)[number]
export type RuleStatus = (typeof RULE_STATUSES)[number]
export type ReviewDecision = (typeof REVIEW_DECISIONS)[number]
export type SlotStatus = (typeof SLOT_STATUSES)[number]

export const TIER_LABELS: Record<StoreTier, string> = {
  high: '高客流店',
  mid: '中客流店',
  low: '低客流店',
}

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  queued: '排队中',
  running: '挖掘中',
  succeeded: '已完成',
  failed: '失败',
}

export const RULE_STATUS_LABELS: Record<RuleStatus, string> = {
  candidate: '待复核',
  adopted: '已采纳',
  rejected: '已驳回',
  parked: '已挂起',
}

export const REVIEW_DECISION_LABELS: Record<ReviewDecision, string> = {
  adopt: '采纳',
  reject: '驳回',
  park: '挂起',
}

export const SLOT_STATUS_LABELS: Record<SlotStatus, string> = {
  draft: '待发布',
  published: '已发布',
  archived: '已归档',
}

export const CHANNEL_LABELS: Record<string, string> = {
  pos: '收银机 POS',
  self_checkout: '自助收银',
  mini_program: '小程序扫码',
}
