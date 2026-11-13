import { defineStore } from 'pinia'
import { createRun, fetchDataset, fetchItemsets, fetchRun, fetchRuns } from '../api/mining'
import type { DatasetSummary, ItemsetRow, MiningRun, RunParams } from '../types/domain'

const DEFAULT_PARAMS: RunParams = {
  min_support: 0.01,
  min_confidence: 0.05,
  max_itemset: 3,
  filter_lift: 1.2,
  filter_confidence: 0.25,
}

interface MiningState {
  dataset: DatasetSummary | null
  runs: MiningRun[]
  current: MiningRun | null
  itemsets: ItemsetRow[]
  itemsetTotal: number
  params: RunParams
  loading: boolean
  running: boolean
  error: string
  pollTimer: number | null
}

export const useMiningStore = defineStore('mining', {
  state: (): MiningState => ({
    dataset: null,
    runs: [],
    current: null,
    itemsets: [],
    itemsetTotal: 0,
    params: { ...DEFAULT_PARAMS },
    loading: false,
    running: false,
    error: '',
    pollTimer: null,
  }),
  getters: {
    summary: (state) => state.current?.summary ?? null,
    isBusy: (state): boolean =>
      state.current?.status === 'queued' || state.current?.status === 'running',
  },
  actions: {
    async loadDataset() {
      this.loading = true
      this.error = ''
      try {
        this.dataset = await fetchDataset()
      } catch (error) {
        this.error = (error as Error).message
      } finally {
        this.loading = false
      }
    },
    async loadRuns() {
      try {
        const result = await fetchRuns(12)
        this.runs = result.runs
        if (!this.current && this.runs.length) {
          this.current = this.runs[0]
        }
      } catch (error) {
        this.error = (error as Error).message
      }
    },
    async runMining() {
      this.running = true
      this.error = ''
      try {
        const run = await createRun(this.params)
        this.current = run
        this.runs = [run, ...this.runs.filter((item) => item.id !== run.id)]
        await this.pollRun(run.id)
        return this.current
      } catch (error) {
        this.error = (error as Error).message
        this.running = false
        throw error
      }
    },
    async pollRun(runId: string) {
      this.running = true
      try {
        for (let attempt = 0; attempt < 30; attempt += 1) {
          const run = await fetchRun(runId)
          this.current = run
          if (run.status === 'succeeded' || run.status === 'failed') {
            if (run.status === 'failed') {
              this.error = run.error ?? '挖掘任务执行失败'
            } else {
              await this.loadItemsets(run.id)
              await this.loadRuns()
            }
            break
          }
          await new Promise((resolve) => setTimeout(resolve, 1200))
        }
      } catch (error) {
        this.error = (error as Error).message
      } finally {
        this.running = false
      }
    },
    async loadItemsets(runId: string, size?: number) {
      try {
        const result = await fetchItemsets(runId, 0, 40, size)
        this.itemsets = result.rows
        this.itemsetTotal = result.total
      } catch (error) {
        this.error = (error as Error).message
      }
    },
    async openRun(run: MiningRun) {
      this.current = run
      this.error = ''
      if (run.status === 'succeeded') {
        await this.loadItemsets(run.id)
      }
    },
    resetParams() {
      this.params = { ...DEFAULT_PARAMS }
    },
  },
})
