import { computed, reactive } from 'vue'

export interface RuleFilterState {
  q: string
  status: string
  stable: '' | 'true' | 'false'
  minLift: number
  sort: string
  direction: 'desc' | 'asc'
}

/** 规则列表筛选条件 → 查询参数（后端负责过滤与排序）。 */
export function useRuleFilter() {
  const state = reactive<RuleFilterState>({
    q: '',
    status: '',
    stable: '',
    minLift: 0,
    sort: 'uplift',
    direction: 'desc',
  })

  const query = computed(() => {
    const payload: Record<string, string | number | boolean> = {
      sort: state.sort,
      direction: state.direction,
    }
    if (state.q.trim()) payload.q = state.q.trim()
    if (state.status) payload.status = state.status
    if (state.stable) payload.stable = state.stable === 'true'
    if (state.minLift > 0) payload.min_lift = state.minLift
    return payload
  })

  function reset() {
    state.q = ''
    state.status = ''
    state.stable = ''
    state.minLift = 0
    state.sort = 'uplift'
    state.direction = 'desc'
  }

  return { state, query, reset }
}
