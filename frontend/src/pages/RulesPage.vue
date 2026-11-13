<template>
  <div class="rules">
    <PageHeader
      eyebrow="02 · 规则筛选与批量采纳"
      title="规则复核"
      :description="`过滤后规则按预估月增量排序；同一商品对只保留置信度更高（前项为小众品）的方向。批次 ${rules.run?.run_label ?? '—'}`"
    >
      <template #actions>
        <a
          class="btn"
          :class="{ 'is-disabled': !canExport }"
          :href="canExport ? downloadUrl : undefined"
          :aria-disabled="!canExport"
          data-test="export-rules"
          @click="onExport"
        >
          导出规则 CSV
        </a>
        <button
          class="btn btn--mint"
          type="button"
          data-test="bulk-adopt"
          :disabled="!canReview || !selected.length"
          @click="adoptSelected"
        >
          批量采纳{{ selected.length ? `（${selected.length}）` : '' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="!canReview" class="notice notice--tag">{{ MESSAGES.viewerHint }}</div>
    <div v-if="rules.error" class="notice notice--alert">{{ rules.error }}</div>
    <div v-else-if="rules.notice" class="notice notice--mint" data-test="rules-notice">{{ rules.notice }}</div>

    <div class="strip">
      <StatSlip :items="stats" />
    </div>

    <ShelfBand index="01" title="筛选" caption="筛选在后端执行，排序按当前选择回传">
      <div class="filters">
        <label class="filter filter--grow">
          <span class="label">关键词</span>
          <input v-model="filter.state.q" class="field" type="search" placeholder="啤酒 / 花生 / 规则键" @keyup.enter="apply" />
        </label>
        <label class="filter">
          <span class="label">状态</span>
          <select v-model="filter.state.status" class="field">
            <option value="">全部</option>
            <option v-for="status in RULE_STATUSES" :key="status" :value="status">
              {{ RULE_STATUS_LABELS[status] }}
            </option>
          </select>
        </label>
        <label class="filter">
          <span class="label">稳定性</span>
          <select v-model="filter.state.stable" class="field">
            <option value="">全部</option>
            <option value="true">三层稳定</option>
            <option value="false">观察</option>
          </select>
        </label>
        <label class="filter filter--num">
          <span class="label">lift ≥</span>
          <input v-model.number="filter.state.minLift" class="field" type="number" step="0.05" min="0" />
        </label>
        <label class="filter">
          <span class="label">排序</span>
          <select v-model="filter.state.sort" class="field">
            <option value="uplift">预估月增量</option>
            <option value="lift">提升度</option>
            <option value="confidence">置信度</option>
            <option value="cooccur">共现小票数</option>
            <option value="ci_low">CI 下界</option>
          </select>
        </label>
        <div class="filter filter--actions">
          <button class="btn btn--sm" type="button" @click="apply">应用</button>
          <button class="btn btn--sm btn--quiet" type="button" @click="reset">重置</button>
        </div>
      </div>
    </ShelfBand>

    <ShelfBand
      index="02"
      title="规则清单"
      :caption="`${rules.stats.total} 条 · 已采纳 ${rules.stats.adopted} 条 · 规则月增量合计 ${formatCurrency(rules.stats.total_uplift)}（未去冲突组）`"
    >
      <div v-if="rules.loading" class="muted">加载中…</div>
      <EmptyState
        v-else-if="!rules.rules.length"
        title="这批参数下没有可复核的规则"
        :hint="MESSAGES.emptyRules"
      >
        <template #action>
          <RouterLink class="btn btn--sm" to="/mining">回到规则挖掘</RouterLink>
        </template>
      </EmptyState>
      <table v-else class="grid-table" data-test="rules-table">
        <thead>
          <tr>
            <th class="col-check">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            </th>
            <th>规则</th>
            <th class="ta-r">支持度</th>
            <th class="ta-r">置信度</th>
            <th class="ta-r">提升度</th>
            <th class="ta-r">CI 区间</th>
            <th>三层 lift</th>
            <th>稳定性</th>
            <th>状态</th>
            <th class="ta-r">预估月增量</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="rule in rules.rules" :key="rule.id">
            <td class="col-check">
              <input v-model="selected" type="checkbox" :value="rule.id" />
            </td>
            <td>
              <RouterLink class="rule-link" :to="`/rules/${rule.id}`">
                <span class="rule-link__pair">{{ rule.antecedent_labels.join(' + ') }}</span>
                <span class="rule-link__arrow">→</span>
                <span class="rule-link__pair">{{ rule.consequent_labels.join(' + ') }}</span>
              </RouterLink>
              <div class="rule-sub">{{ rule.zone }} · 冲突组 {{ rule.conflict_group }}</div>
            </td>
            <td class="ta-r is-num">{{ formatPercent(rule.support) }}</td>
            <td class="ta-r is-num">{{ formatPercent(rule.confidence) }}</td>
            <td class="ta-r is-num rule-lift">{{ rule.lift.toFixed(2) }}</td>
            <td class="ta-r is-num">[{{ rule.ci_low?.toFixed(2) }}, {{ rule.ci_high?.toFixed(2) }}]</td>
            <td class="is-num tier-cell">
              {{ rule.tier_lifts.high?.toFixed(2) }} / {{ rule.tier_lifts.mid?.toFixed(2) }} /
              {{ rule.tier_lifts.low?.toFixed(2) }}
            </td>
            <td>
              <span :class="['chip', rule.stable ? 'chip--mint' : 'chip--tag']">
                {{ rule.stable ? '三层稳定' : '观察' }}
              </span>
            </td>
            <td>
              <span :class="['chip', statusTone(rule.status)]">{{ RULE_STATUS_LABELS[rule.status] }}</span>
            </td>
            <td class="ta-r is-num">{{ formatCurrency(rule.uplift_month) }}</td>
            <td class="ta-r">
              <RouterLink class="btn btn--sm btn--quiet" :to="`/rules/${rule.id}`">详情</RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </ShelfBand>

    <ShelfBand index="03" title="复核口径" caption="写入审计日志；驳回与挂起必须填理由">
      <div class="criteria">
        <div>
          <div class="label">稳定</div>
          <p>高/中/低客流三层 lift 均 &gt; 1.15，且 Wilson 95% 区间下界均 &gt; 1。</p>
        </div>
        <div>
          <div class="label">增量</div>
          <p>共现小票数 × 客单均值 × 采纳率 0.35 × (30 / 样本 7 天)，四舍五入到分。</p>
        </div>
        <div>
          <div class="label">冲突组</div>
          <p>同一货架分区只取增量更高的一条；被剔除规则仍留在列表里可单独采纳。</p>
        </div>
      </div>
    </ShelfBand>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ShelfBand from '../components/common/ShelfBand.vue'
import StatSlip, { type SlipItem } from '../components/common/StatSlip.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { useRuleStore } from '../stores/ruleStore'
import { useAuthStore } from '../stores/authStore'
import { useRuleFilter } from '../hooks/useRuleFilter'
import { MESSAGES } from '../constants/messages'
import { RULE_STATUSES, RULE_STATUS_LABELS } from '../constants/enums'
import { formatCurrency, formatPercent } from '../utils/format'
import { rulesExportUrl } from '../api/rules'

const rules = useRuleStore()
const auth = useAuthStore()
const filter = useRuleFilter()
const selected = ref<string[]>([])

const canReview = computed(() => auth.can('rules:review'))
const canExport = computed(() => auth.can('rules:export'))
const downloadUrl = computed(() => rulesExportUrl(rules.run?.id))

const allSelected = computed(
  () => rules.rules.length > 0 && selected.value.length === rules.rules.length,
)

const stats = computed<SlipItem[]>(() => [
  { label: '规则', value: rules.stats.total, unit: '条' },
  { label: '三层稳定', value: rules.stats.stable, unit: '条', tone: 'mint' },
  { label: '已采纳', value: rules.stats.adopted, unit: '条' },
  { label: '待复核', value: rules.stats.candidate, unit: '条' },
  {
    label: '规则月增量合计',
    value: formatCurrency(rules.stats.total_uplift),
    tone: 'mint',
    hint: '含冲突组重复，建议单口径见陈列页',
  },
])

function statusTone(status: string): string {
  if (status === 'adopted') return 'chip--mint'
  if (status === 'rejected') return 'chip--alert'
  if (status === 'parked') return 'chip--tag'
  return ''
}

async function apply() {
  selected.value = []
  await rules.load(filter.query.value)
}

function reset() {
  filter.reset()
  void apply()
}

function toggleAll() {
  selected.value = allSelected.value ? [] : rules.rules.map((rule) => rule.id)
}

async function adoptSelected() {
  if (!selected.value.length) return
  try {
    await rules.bulkAdopt(selected.value, '早高峰关联组合，先上 3 条试点（批量采纳）')
    selected.value = []
  } catch {
    /* store 已记录错误 */
  }
}

function onExport(event: MouseEvent) {
  if (!canExport.value) {
    event.preventDefault()
    rules.error = '当前角色无导出权限（后端返回 403）'
  }
}

onMounted(async () => {
  await rules.load(filter.query.value)
})
</script>

<style scoped>
.rules {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.notice {
  margin-top: 12px;
  padding: 8px 12px;
  font-size: 12px;
  border: 1px dashed var(--shelf);
  background: var(--paper-2);
}
.notice--tag {
  border-color: var(--tag-deep);
  background: var(--tag-pale);
}
.notice--mint {
  border-color: var(--mint-deep);
  background: var(--mint-pale);
  color: var(--mint-ink);
}
.notice--alert {
  border-color: var(--alert);
  background: var(--alert-pale);
  color: var(--alert);
}
.strip {
  margin-top: 14px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}
.filter {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 128px;
}
.filter--grow {
  flex: 1 1 220px;
}
.filter--num {
  max-width: 96px;
}
.filter--actions {
  flex-direction: row;
  gap: 6px;
  min-width: 0;
}
.muted {
  font-size: 12px;
  color: var(--ink-faint);
  padding: 8px 0;
}
.col-check {
  width: 30px;
}
.ta-r {
  text-align: right;
}
.rule-link {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 5px;
  color: var(--ink);
  font-weight: 500;
}
.rule-link:hover {
  text-decoration: none;
  color: var(--mint-ink);
}
.rule-link__pair {
  border-bottom: 1px solid var(--shelf-soft);
}
.rule-link__arrow {
  color: var(--tag-deep);
}
.rule-sub {
  font-size: 10px;
  color: var(--ink-faint);
  margin-top: 2px;
}
.rule-lift {
  font-weight: 700;
  color: var(--mint-ink);
}
.tier-cell {
  font-size: 11px;
  color: var(--ink-soft);
  white-space: nowrap;
}
.criteria {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px 22px;
}
.criteria p {
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--ink-soft);
}
a.is-disabled {
  opacity: 0.45;
  pointer-events: none;
}
@media (max-width: 767px) {
  .filter {
    min-width: 0;
    flex: 1 1 42%;
  }
  .filter--grow {
    flex: 1 1 100%;
  }
}
</style>
