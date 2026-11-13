import http from './http'
import type { RuleDetail, RulesResponse } from '../types/domain'

export interface RuleQuery {
  run_id?: string
  status?: string
  stable?: boolean
  min_lift?: number
  q?: string
  sort?: string
  direction?: string
  page?: number
  page_size?: number
}

export async function fetchRules(query: RuleQuery = {}): Promise<RulesResponse> {
  const { data } = await http.get<RulesResponse>('/rules', { params: query })
  return data
}

export async function fetchRule(id: string): Promise<RuleDetail> {
  const { data } = await http.get<RuleDetail>(`/rules/${id}`)
  return data
}

export async function reviewRule(
  id: string,
  decision: 'adopt' | 'reject' | 'park',
  reason: string,
): Promise<RuleDetail> {
  const { data } = await http.post<RuleDetail>(`/rules/${id}/review`, { decision, reason })
  return data
}

export async function batchReview(
  ruleIds: string[],
  decision: 'adopt' | 'reject' | 'park',
  reason: string,
): Promise<{ updated: number }> {
  const { data } = await http.post('/rules/batch-review', {
    rule_ids: ruleIds,
    decision,
    reason,
  })
  return data
}

export function rulesExportUrl(runId?: string): string {
  return runId ? `/api/rules/export.csv?run_id=${runId}` : '/api/rules/export.csv'
}
