import { defineStore } from 'pinia'
import { fetchIngestBatch, fetchIngestSummary, importBatch, importDemo, type ImportPayload } from '../api/ingest'
import type { IngestBatch, IngestSummary } from '../types/domain'

interface IngestState {
  summary: IngestSummary | null
  selected: IngestBatch | null
  loading: boolean
  working: boolean
  error: string
  notice: string
}

export const useIngestStore = defineStore('ingest', {
  state: (): IngestState => ({
    summary: null,
    selected: null,
    loading: false,
    working: false,
    error: '',
    notice: '',
  }),
  getters: {
    latest: (state): IngestBatch | null => state.summary?.latest ?? null,
    lastCounts: (state) => state.summary?.last_counts ?? null,
    finalBaskets: (state) => state.summary?.final_baskets ?? [],
    batches: (state) => state.summary?.batches ?? [],
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.summary = await fetchIngestSummary()
        this.selected = this.summary.latest
      } catch (error) {
        this.error = (error as Error).message
      } finally {
        this.loading = false
      }
    },
    async submit(payload: ImportPayload) {
      this.working = true
      this.error = ''
      this.notice = ''
      try {
        this.summary = await importBatch(payload)
        this.selected = this.summary.latest
        this.notice = `批次 ${payload.batch_no} 已入库：接收 ${this.summary.last_counts.received} · 重复 ${this.summary.last_counts.duplicate} · 作废 ${this.summary.last_counts.voided} · 更正 ${this.summary.last_counts.corrected} · 拒绝 ${this.summary.last_counts.rejected}`
      } catch (error) {
        this.error = (error as Error).message
        throw error
      } finally {
        this.working = false
      }
    },
    async loadDemo() {
      this.working = true
      this.error = ''
      this.notice = ''
      try {
        this.summary = await importDemo('演示批次：重复 / 作废 / 更正 / 拒绝各至少一条')
        this.selected = this.summary.latest
        this.notice = '已生成一条演示补传批次，可直接核对五类计数与最终有效小票。'
      } catch (error) {
        this.error = (error as Error).message
        throw error
      } finally {
        this.working = false
      }
    },
    async openBatch(batchNo: string) {
      this.error = ''
      try {
        this.selected = await fetchIngestBatch(batchNo)
      } catch (error) {
        this.error = (error as Error).message
      }
    },
  },
})
