import http from './http'
import type { DatasetSummary, ItemsetRow, MiningRun, RunParams } from '../types/domain'

export async function fetchDataset(): Promise<DatasetSummary> {
  const { data } = await http.get<DatasetSummary>('/baskets/summary')
  return data
}

export async function fetchRuns(limit = 10): Promise<{ runs: MiningRun[]; count: number }> {
  const { data } = await http.get('/mining/runs', { params: { limit } })
  return data
}

export async function createRun(params: RunParams): Promise<MiningRun> {
  const { data } = await http.post<MiningRun>('/mining/runs', params)
  return data
}

export async function fetchRun(runId: string, withItemsets = false): Promise<MiningRun> {
  const { data } = await http.get<MiningRun>(`/mining/runs/${runId}`, {
    params: { with_itemsets: withItemsets },
  })
  return data
}

export async function fetchItemsets(
  runId: string,
  offset = 0,
  limit = 50,
  size?: number,
): Promise<{ total: number; offset: number; limit: number; rows: ItemsetRow[] }> {
  const { data } = await http.get(`/mining/runs/${runId}/itemsets`, {
    params: { offset, limit, size },
  })
  return data
}
