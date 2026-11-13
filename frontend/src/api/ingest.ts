import http from './http'
import type { IngestBatch, IngestSummary } from '../types/domain'

export async function fetchIngestSummary(): Promise<IngestSummary> {
  const { data } = await http.get<IngestSummary>('/ingest/summary')
  return data
}

export interface IngestRecordInput {
  record_id: string
  record_type: 'supplement' | 'void' | 'correction'
  basket_no: string
  occurred_at: string
  source_seq?: number
  same_as_no?: string
  reason?: string
  store_code?: string
  store_name?: string
  store_tier?: 'high' | 'mid' | 'low'
  channel?: string
  lines?: Array<{ sku: string; qty: number; amount: number }>
}

export interface ImportPayload {
  batch_no: string
  file_name?: string
  source?: string
  note?: string
  records: IngestRecordInput[]
}

export async function importBatch(payload: ImportPayload): Promise<IngestSummary> {
  const { data } = await http.post<IngestSummary>('/ingest/import', payload)
  return data
}

export async function importDemo(note = ''): Promise<IngestSummary> {
  const { data } = await http.post<IngestSummary>('/ingest/demo', { note })
  return data
}

export async function fetchIngestBatch(batchNo: string): Promise<IngestBatch> {
  const { data } = await http.get<IngestBatch>(`/ingest/batches/${batchNo}`)
  return data
}
