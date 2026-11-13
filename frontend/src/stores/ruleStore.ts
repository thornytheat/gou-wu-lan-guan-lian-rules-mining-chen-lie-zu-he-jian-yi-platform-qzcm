import { defineStore } from 'pinia'
import { batchReview, fetchRule, fetchRules, reviewRule, type RuleQuery } from '../api/rules'
import type { Rule, RuleDetail, MiningRun } from '../types/domain'

interface RuleState {
  rules: Rule[]
  run: MiningRun | null
  stats: { total: number; adopted: number; stable: number; candidate: number; total_uplift: number }
  detail: RuleDetail | null
  filters: RuleQuery
  loading: boolean
  error: string
  notice: string
}

const EMPTY_STATS = { total: 0, adopted: 0, stable: 0, candidate: 0, total_uplift: 0 }

export const useRuleStore = defineStore('rules', {
  state: (): RuleState => ({
    rules: [],
    run: null,
    stats: { ...EMPTY_STATS },
    detail: null,
    filters: { sort: 'uplift', direction: 'desc', page_size: 50 },
    loading: false,
    error: '',
    notice: '',
  }),
  getters: {
    selectedTotal: (state): number => state.rules.length,
    canReview: (state): boolean => Boolean(state.run),
  },
  actions: {
    async load(extra: RuleQuery = {}) {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchRules({ ...this.filters, ...extra })
        this.rules = result.rules
        this.run = result.run
        this.stats = result.stats
      } catch (error) {
        this.error = (error as Error).message
      } finally {
        this.loading = false
      }
    },
    async open(id: string) {
      this.loading = true
      this.error = ''
      try {
        this.detail = await fetchRule(id)
      } catch (error) {
        this.error = (error as Error).message
      } finally {
        this.loading = false
      }
    },
    async decide(id: string, decision: 'adopt' | 'reject' | 'park', reason: string) {
      this.error = ''
      this.notice = ''
      try {
        this.detail = await reviewRule(id, decision, reason)
        this.notice =
          decision === 'adopt' ? '已采纳，可进入陈列建议' : decision === 'reject' ? '已驳回' : '已挂起'
        await this.load()
        return this.detail
      } catch (error) {
        this.error = (error as Error).message
        throw error
      }
    },
    async bulkAdopt(ids: string[], reason: string) {
      this.error = ''
      this.notice = ''
      try {
        const result = await batchReview(ids, 'adopt', reason)
        this.notice = `已批量采纳 ${result.updated} 条规则`
        await this.load()
      } catch (error) {
        this.error = (error as Error).message
        throw error
      }
    },
  },
})
