/** 补传导入枚举镜像（后端 backend/src/constants/ingest.py）。 */
export const INGEST_RECORD_TYPES = ['supplement', 'void', 'correction'] as const
export const INGEST_RESULTS = ['received', 'duplicate', 'voided', 'corrected', 'rejected'] as const

export type IngestRecordType = (typeof INGEST_RECORD_TYPES)[number]
export type IngestResult = (typeof INGEST_RESULTS)[number]

export const INGEST_RECORD_TYPE_LABELS: Record<IngestRecordType, string> = {
  supplement: '补传',
  void: '作废',
  correction: '更正',
}

export const INGEST_RESULT_LABELS: Record<IngestResult, string> = {
  received: '接收',
  duplicate: '重复',
  voided: '作废',
  corrected: '更正',
  rejected: '拒绝',
}

export const INGEST_RESULT_TONES: Record<IngestResult, string> = {
  received: 'chip--mint',
  duplicate: 'chip--tag',
  voided: 'chip--alert',
  corrected: 'chip--tag',
  rejected: 'chip--alert',
}
