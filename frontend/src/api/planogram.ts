import http from './http'
import type { Plan, PlanSummary } from '../types/domain'

export async function fetchPlans(): Promise<{ plans: PlanSummary[]; count: number }> {
  const { data } = await http.get('/planogram')
  return data
}

export async function fetchPlan(planCode: string): Promise<Plan> {
  const { data } = await http.get<Plan>(`/planogram/${planCode}`)
  return data
}

export async function generatePlan(runId?: string): Promise<Plan> {
  const { data } = await http.post<Plan>('/planogram/generate', { run_id: runId ?? null })
  return data
}

export async function publishPlan(planCode: string): Promise<Plan> {
  const { data } = await http.post<Plan>(`/planogram/${planCode}/publish`)
  return data
}

export async function updateSlot(
  slotId: string,
  status: 'draft' | 'published' | 'archived',
  note = '',
): Promise<Plan> {
  const { data } = await http.patch<Plan>(`/planogram/slots/${slotId}`, { status, note })
  return data
}

export function planogramExportUrl(planCode: string): string {
  return `/api/planogram/${planCode}/export`
}
