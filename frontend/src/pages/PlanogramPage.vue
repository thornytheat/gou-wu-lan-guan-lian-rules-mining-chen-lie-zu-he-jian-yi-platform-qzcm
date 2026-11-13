<template>
  <div class="planogram">
    <PageHeader
      eyebrow="03 · 货架位分配与工单"
      title="陈列建议"
      :description="`K=6 贪心背包按「增量 / 冲突组占用」选位；同一货架分区只取一条。当前建议单 ${plan?.plan_code ?? '—'}`"
    >
      <template #actions>
        <select v-if="plans.length" class="field plan-select" :value="plan?.plan_code" @change="onSelect">
          <option v-for="item in plans" :key="item.plan_code" :value="item.plan_code">
            {{ item.plan_code }} · {{ item.slot_count }} 位 · {{ SLOT_STATUS_LABELS[item.status] }}
          </option>
        </select>
        <button
          class="btn"
          type="button"
          data-test="generate-plan"
          :disabled="!canWrite || working"
          :title="canWrite ? '' : '店长账号无生成权限（后端返回 403）'"
          @click="generate"
        >
          生成陈列建议
        </button>
        <button
          class="btn btn--mint"
          type="button"
          data-test="publish-plan"
          :disabled="!canPublish || working || !plan || plan.status === 'published'"
          :title="canPublish ? '' : '仅品类总监可发布'"
          @click="publish"
        >
          {{ plan?.status === 'published' ? '已发布' : '发布建议单' }}
        </button>
        <a
          class="btn"
          :class="{ 'is-disabled': !canExport }"
          :href="canExport && plan ? downloadUrl : undefined"
          data-test="export-workorder"
          @click="onExport"
        >
          导出工单 CSV
        </a>
      </template>
    </PageHeader>

    <div v-if="!canWrite" class="notice notice--tag">{{ MESSAGES.viewerHint }}</div>
    <div v-if="store.error" class="notice notice--alert">{{ store.error }}</div>
    <div v-else-if="store.notice" class="notice notice--mint" data-test="plan-notice">{{ store.notice }}</div>

    <EmptyState
      v-if="!plan"
      title="还没有陈列建议单"
      :hint="MESSAGES.emptyPlans"
    >
      <template #action>
        <RouterLink class="btn btn--sm" to="/mining">先去跑一次挖掘</RouterLink>
      </template>
    </EmptyState>

    <template v-else>
      <div class="strip">
        <StatSlip :items="stats" />
      </div>

      <div class="board">
        <div class="board__endcap">
          <div class="board__endcap-left">
            <span class="eyebrow">endcap · planogram</span>
            <span class="board__code">{{ plan.plan_code }}</span>
            <span class="board__run">来源批次 {{ plan.run_label }}</span>
          </div>
          <div class="board__endcap-right">
            <span :class="['chip', plan.status === 'published' ? 'chip--mint' : 'chip--tag']">
              {{ SLOT_STATUS_LABELS[plan.status] }}
            </span>
            <span class="board__total tag-num">{{ formatCurrency(plan.total_uplift) }}<small>/月</small></span>
          </div>
        </div>

        <div class="shelves">
          <article v-for="slot in plan.slots" :key="slot.id" class="shelf">
            <div class="shelf__marker">
              <span class="shelf__index">{{ String(slot.position_index).padStart(2, '0') }}</span>
              <span class="shelf__zone">{{ slot.zone }}</span>
              <span class="shelf__label">{{ slot.shelf_label }}</span>
            </div>

            <div class="shelf__goods">
              <div class="good good--lead">
                <span class="good__name">{{ slot.rule?.antecedent_labels.join(' + ') }}</span>
                <span class="good__tag">前项 · {{ slot.rule ? formatPercent(slot.rule.confidence) : '—' }} 连带</span>
              </div>
              <span class="shelf__arrow">→</span>
              <div class="good">
                <span class="good__name">{{ slot.rule?.consequent_labels.join(' + ') }}</span>
                <span class="good__tag">后项 · lift {{ slot.rule?.lift.toFixed(2) }}</span>
              </div>
            </div>

            <div class="shelf__side">
              <span class="price-tag shelf__price">
                <span class="shelf__price-label">预估月增量</span>
                <span class="shelf__price-num">{{ formatCurrency(slot.est_uplift) }}</span>
              </span>
              <div class="shelf__chips">
                <span :class="['chip', slot.rule?.stable ? 'chip--mint' : 'chip--tag']">
                  {{ slot.rule?.stable ? '三层稳定' : '观察' }}
                </span>
                <span class="chip">{{ slot.conflict_group }}</span>
                <span v-if="slot.rule" class="chip" :class="slot.rule.status === 'adopted' ? 'chip--mint' : ''">
                  {{ RULE_STATUS_LABELS[slot.rule.status] }}
                </span>
                <RouterLink v-if="slot.rule" class="shelf__link" :to="`/rules/${slot.rule.id}`">规则详情</RouterLink>
              </div>
              <p class="shelf__hint">{{ slot.buyer_hint || slot.note }}</p>
            </div>
          </article>
        </div>

        <div class="floor">
          <span class="floor__line" />
          <span class="floor__text">地面 · 收银动线方向</span>
        </div>
      </div>

      <div class="columns">
        <ShelfBand index="01" title="冲突组消解" :caption="`K = ${plan.params.shelf_slots ?? 6}，实际占位 ${plan.slot_count}；同组只取增量更高的一条`">
          <div v-if="!plan.skipped.length" class="muted">没有规则因冲突被剔除。</div>
          <ul v-else class="skipped">
            <li v-for="item in plan.skipped" :key="item.rule_key">
              <span class="chip chip--alert">剔除</span>
              <span class="skipped__label">{{ item.label }}</span>
              <span class="skipped__reason">{{ item.reason }}</span>
            </li>
          </ul>
        </ShelfBand>

        <ShelfBand index="02" title="工单说明" caption="导出 CSV 给店长执行，行数 = 建议位数">
          <dl class="facts">
            <div>
              <dt>执行动作</dt>
              <dd>按货架位把后项商品移到前项旁，价签换成组合价签；一周后回看连带率。</dd>
            </div>
            <div>
              <dt>增量口径</dt>
              <dd>
                共现小票数 × 客单均值 {{ formatCurrency(meanAmount) }} × 采纳率 {{ adoptionRate }} × 月化系数
                {{ monthlyFactor }}
              </dd>
            </div>
            <div>
              <dt>职责边界</dt>
              <dd>品类总监发布建议单；店长只读执行；运营可重复生成草稿对比。</dd>
            </div>
          </dl>
        </ShelfBand>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ShelfBand from '../components/common/ShelfBand.vue'
import StatSlip, { type SlipItem } from '../components/common/StatSlip.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { usePlanogramStore } from '../stores/planogramStore'
import { useAuthStore } from '../stores/authStore'
import { MESSAGES } from '../constants/messages'
import { RULE_STATUS_LABELS, SLOT_STATUS_LABELS } from '../constants/enums'
import { formatCurrency, formatPercent } from '../utils/format'
import { planogramExportUrl } from '../api/planogram'

const store = usePlanogramStore()
const auth = useAuthStore()
const working = ref(false)

const plan = computed(() => store.current)
const plans = computed(() => store.plans)
const canWrite = computed(() => auth.can('planogram:write'))
const canPublish = computed(() => auth.can('planogram:publish'))
const canExport = computed(() => auth.can('rules:export'))
const downloadUrl = computed(() => (plan.value ? planogramExportUrl(plan.value.plan_code) : '#'))
const monthlyFactor = computed(() => (plan.value?.basis?.monthly_factor ?? 0).toFixed(2))
const meanAmount = computed(() => plan.value?.basis?.mean_amount ?? 0)
const adoptionRate = computed(() => (plan.value?.basis?.adoption_rate ?? 0).toFixed(2))

const stats = computed<SlipItem[]>(() => {
  const row = plan.value
  if (!row) return []
  return [
    { label: '建议位', value: row.slot_count, unit: '个', tone: 'mint' },
    { label: '冲突剔除', value: row.skipped.length, unit: '条' },
    { label: '合计月增量', value: formatCurrency(row.total_uplift), tone: 'mint', hint: `${row.slot_count} 席合计` },
    {
      label: '状态',
      value: SLOT_STATUS_LABELS[row.status],
      hint: row.published_at ? '已同步店长端' : '待总监发布',
    },
    { label: '来源批次', value: row.run_label.replace('RUN-', ''), hint: row.plan_code },
  ]
})

async function loadAll() {
  await store.load()
}

async function generate() {
  working.value = true
  try {
    await store.generate()
  } catch {
    /* store 已记录 */
  } finally {
    working.value = false
  }
}

async function publish() {
  if (!plan.value) return
  working.value = true
  try {
    await store.publish(plan.value.plan_code)
  } catch {
    /* store 已记录 */
  } finally {
    working.value = false
  }
}

function onSelect(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  void store.open(value)
}

function onExport(event: MouseEvent) {
  if (!canExport.value) {
    event.preventDefault()
    store.error = '当前角色无导出权限（后端返回 403）'
  }
}

onMounted(loadAll)
</script>

<style scoped>
.planogram {
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
.plan-select {
  max-width: 250px;
  font-size: 11.5px;
}
.strip {
  margin-top: 14px;
}
.board {
  margin-top: 24px;
  border: 1px solid var(--shelf);
  background: var(--paper-2);
}
.board__endcap {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: var(--mint);
  color: var(--mint-ink);
  border-bottom: 2px solid var(--mint-deep);
}
.board__endcap-left {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.board__endcap-left .eyebrow {
  color: var(--mint-ink);
  opacity: 0.75;
}
.board__code {
  font-family: var(--tag-font);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.board__run {
  font-size: 10.5px;
  opacity: 0.8;
}
.board__endcap-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.board__total {
  font-size: 22px;
  font-weight: 700;
}
.board__total small {
  font-size: 11px;
  font-weight: 400;
  margin-left: 2px;
}
.shelves {
  display: flex;
  flex-direction: column;
}
.shelf {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr) 240px;
  gap: 16px;
  align-items: center;
  padding: 13px 16px 15px;
  border-bottom: var(--shelf-line);
  position: relative;
}
.shelf::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 9px;
  background: linear-gradient(0deg, oklch(55% 0.02 76 / 0.13), transparent);
  pointer-events: none;
}
.shelf__marker {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.shelf__index {
  font-family: var(--tag-font);
  font-size: 12px;
  font-weight: 600;
  color: var(--tag-deep);
}
.shelf__zone {
  font-size: 12.5px;
  font-weight: 500;
}
.shelf__label {
  font-size: 10px;
  color: var(--ink-faint);
}
.shelf__goods {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.good {
  border: 1px solid var(--shelf-soft);
  background: var(--paper);
  padding: 7px 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  border-top: 2px solid var(--shelf);
}
.good--lead {
  border-top-color: var(--tag-deep);
  background: var(--tag-pale);
}
.good__name {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.good__tag {
  font-family: var(--tag-font);
  font-size: 9.5px;
  letter-spacing: 0.04em;
  color: var(--ink-faint);
}
.shelf__arrow {
  font-size: 14px;
  color: var(--tag-deep);
}
.shelf__side {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}
.shelf__price {
  display: inline-flex;
  flex-direction: column;
  padding: 5px 9px 4px;
}
.shelf__price-label {
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: oklch(42% 0.05 80);
}
.shelf__price-num {
  font-family: var(--tag-font);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.shelf__chips {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}
.shelf__link {
  font-size: 10.5px;
}
.shelf__hint {
  font-size: 10px;
  color: var(--ink-faint);
  max-width: 30ch;
}
.floor {
  padding: 10px 16px 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.floor__line {
  flex: 1;
  height: 2px;
  background: repeating-linear-gradient(90deg, var(--shelf) 0 12px, transparent 12px 20px);
}
.floor__text {
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.columns {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 28px;
  align-items: start;
}
.muted {
  font-size: 12px;
  color: var(--ink-faint);
  padding: 6px 0;
}
.skipped {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.skipped li {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  border-left: 2px solid var(--alert);
  padding-left: 8px;
  font-size: 11.5px;
}
.skipped__label {
  font-weight: 500;
}
.skipped__reason {
  font-size: 10.5px;
  color: var(--ink-faint);
}
.facts {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.facts dt {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.facts dd {
  margin: 1px 0 0;
  font-size: 11.5px;
  color: var(--ink-soft);
}
a.is-disabled {
  opacity: 0.45;
  pointer-events: none;
}
@media (max-width: 1279px) {
  .shelf {
    grid-template-columns: 140px minmax(0, 1fr);
  }
  .shelf__side {
    grid-column: 1 / -1;
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }
  .shelf__hint {
    max-width: none;
  }
}
@media (max-width: 1023px) {
  .columns {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 767px) {
  .shelf {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
  }
  .shelf__goods {
    flex-direction: column;
    align-items: stretch;
  }
  .shelf__arrow {
    text-align: center;
    transform: rotate(90deg);
  }
  .board__endcap {
    align-items: flex-start;
  }
}
</style>
