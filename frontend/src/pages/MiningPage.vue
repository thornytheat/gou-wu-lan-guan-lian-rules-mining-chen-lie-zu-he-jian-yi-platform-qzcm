<template>
  <div class="mining">
    <PageHeader
      eyebrow="01 · 挖掘参数与频繁项集"
      title="规则挖掘"
      description="Apriori 在 3,000 张小票上逐层生成候选项集并计数；前端只提交参数，所有计数、规则指标与稳定性结论都由后端回传。"
    >
      <template #actions>
        <button class="btn btn--quiet" type="button" @click="mining.resetParams()">重置参数</button>
        <button
          class="btn btn--mint"
          type="button"
          data-test="run-mining"
          :disabled="!canRun || mining.running"
          :title="canRun ? '' : '店长账号无挖掘权限（后端会返回 403）'"
          @click="run"
        >
          {{ mining.running ? '挖掘中…' : '运行挖掘' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="!canRun" class="notice notice--tag">
      当前是店长账号：可以查看挖掘结果与规则详情，但「运行挖掘」「读取 POS 明细」都会返回 403。
      用 analyst 或 admin 账号体验完整链路。
    </div>

    <ErrorNotice v-if="mining.error" :message="mining.error" @retry="bootstrap" />

    <div class="strip">
      <StatSlip :items="datasetTags" />
      <span v-if="!canReadBaskets" class="strip__hint">店长账号不展示 POS 明细（/api/baskets/summary → 403）</span>
    </div>

    <div class="columns">
      <section class="col">
        <ShelfBand index="01" title="挖掘参数" caption="min_support 决定候选规模，过滤阈值决定可执行条数">
          <div class="params">
            <label class="param">
              <span class="label">最小支持度 min_support</span>
              <input v-model.number="mining.params.min_support" class="field" type="number" step="0.005" min="0.005" max="0.5" data-test="min-support" />
              <span class="param__hint">1% = 30 张小票；低于阈值的项集不进入候选</span>
            </label>
            <label class="param">
              <span class="label">规则置信度下限</span>
              <input v-model.number="mining.params.min_confidence" class="field" type="number" step="0.01" min="0.01" max="1" />
              <span class="param__hint">生成方向规则时的门槛（默认 0.05）</span>
            </label>
            <label class="param">
              <span class="label">最大项集长度</span>
              <select v-model.number="mining.params.max_itemset" class="field">
                <option :value="2">2（只挖商品对）</option>
                <option :value="3">3（含三元组）</option>
                <option :value="4">4</option>
              </select>
              <span class="param__hint">demo 样本下 3 项集无达标组合</span>
            </label>
            <label class="param">
              <span class="label">过滤：lift 下限</span>
              <input v-model.number="mining.params.filter_lift" class="field" type="number" step="0.05" min="0.5" max="10" />
              <span class="param__hint">计划口径 1.2</span>
            </label>
            <label class="param">
              <span class="label">过滤：置信度下限</span>
              <input v-model.number="mining.params.filter_confidence" class="field" type="number" step="0.01" min="0.05" max="1" />
              <span class="param__hint">计划口径 0.25</span>
            </label>
            <div class="param param--formula">
              <span class="label">指标口径</span>
              <code>conf = sup(A∪B)/sup(A)</code>
              <code>lift = conf/sup(B)</code>
              <code>conviction = (1−sup(B))/(1−conf)</code>
            </div>
          </div>
        </ShelfBand>

        <ShelfBand
          index="03"
          title="频繁项集"
          :caption="`共 ${mining.itemsetTotal} 个达标项集 · 当前批次 ${mining.current?.run_label ?? '—'}`"
        >
          <template #actions>
            <div class="tabs">
              <button
                v-for="tab in sizeTabs"
                :key="tab.value ?? 'all'"
                type="button"
                class="tab"
                :class="{ 'is-on': sizeFilter === tab.value }"
                @click="changeSize(tab.value)"
              >
                {{ tab.label }}
              </button>
            </div>
          </template>
          <div v-if="!mining.itemsets.length" class="muted">还没有批次结果。先运行一次挖掘。</div>
          <table v-else class="grid-table" data-test="itemsets">
            <thead>
              <tr>
                <th>项集</th>
                <th>商品</th>
                <th>长度</th>
                <th class="ta-r">小票数</th>
                <th class="ta-r">支持度</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in mining.itemsets" :key="row.items.join('|')">
                <td class="mono">{{ row.items.join(' · ') }}</td>
                <td>{{ row.labels.join(' + ') }}</td>
                <td>{{ row.size }}</td>
                <td class="ta-r is-num">{{ row.count }}</td>
                <td class="ta-r is-num">{{ formatPercent(row.support) }}</td>
              </tr>
            </tbody>
          </table>
        </ShelfBand>

        <ShelfBand index="04" title="最近批次" caption="点一行查看该批次的项集与规则">
          <div v-if="!mining.runs.length" class="muted">还没有挖掘批次。</div>
          <table v-else class="grid-table">
            <thead>
              <tr>
                <th>批次</th>
                <th>状态</th>
                <th class="ta-r">频繁项集</th>
                <th class="ta-r">候选规则</th>
                <th class="ta-r">过滤后</th>
                <th class="ta-r">耗时</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="run in mining.runs"
                :key="run.id"
                :class="{ 'is-current': run.id === mining.current?.id }"
                @click="openRun(run)"
              >
                <td class="mono">{{ run.run_label }}</td>
                <td>
                  <span :class="['chip', run.status === 'succeeded' ? 'chip--mint' : run.status === 'failed' ? 'chip--alert' : '']">
                    {{ RUN_STATUS_LABELS[run.status] }}
                  </span>
                </td>
                <td class="ta-r is-num">{{ run.frequent_itemsets }}</td>
                <td class="ta-r is-num">{{ run.candidate_rules }}</td>
                <td class="ta-r is-num">{{ run.passed_rules }}</td>
                <td class="ta-r is-num">{{ formatDuration(run.duration_ms) }}</td>
                <td class="mono">{{ formatDateTime(run.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </ShelfBand>

        <ShelfBand index="05" title="小票样本" caption="最近 6 张：来源渠道 / 门店分层 / 明细行">
          <div class="baskets">
            <article v-for="basket in dataset?.sample_baskets ?? []" :key="basket.id" class="basket">
              <div class="basket__head">
                <span class="mono">{{ basket.basket_no }}</span>
                <span class="chip">{{ TIER_LABELS[basket.store_tier] }}</span>
              </div>
              <div class="basket__meta">
                {{ basket.store_name }} · {{ CHANNEL_LABELS[basket.channel] ?? basket.channel }} ·
                {{ formatDateTime(basket.basket_ts) }}
              </div>
              <ul class="basket__lines">
                <li v-for="line in basket.lines" :key="line.sku">
                  <span>{{ line.name }}</span>
                  <span class="tag-num">×{{ line.qty }} · ¥{{ line.amount.toFixed(2) }}</span>
                </li>
              </ul>
              <div class="basket__total">
                <span>{{ basket.item_count }} 行</span>
                <span class="tag-num">{{ formatCurrency(basket.net_amount) }}</span>
              </div>
            </article>
          </div>
        </ShelfBand>
      </section>

      <aside class="col col--side">
        <ShelfBand index="02" title="本次结果" caption="过滤 → 稳定性 → 货架位">
          <div v-if="!summary" class="muted">还没有成功批次。</div>
          <div v-else class="result" data-test="run-status">
            <div class="result__stack">
              <div class="result__row">
                <span>频繁项集</span>
                <span class="tag-num">{{ summary.frequent_itemsets }}</span>
              </div>
              <div class="result__row">
                <span>候选规则（conf ≥ 参数）</span>
                <span class="tag-num">{{ summary.candidate_rules }}</span>
              </div>
              <div class="result__row result__row--strong">
                <span>过滤后（lift &gt; {{ summary.params.filter_lift }} 且 conf &gt; {{ summary.params.filter_confidence }}）</span>
                <span class="tag-num">{{ summary.passed_rules }}</span>
              </div>
              <div class="result__row">
                <span>三层稳定</span>
                <span class="tag-num">{{ summary.stable_rules }}</span>
              </div>
              <div class="result__row">
                <span>建议货架位（K=6，冲突组去重）</span>
                <span class="tag-num">{{ summary.selection.slot_count }}</span>
              </div>
              <div class="result__row result__row--total">
                <span>预估月增量</span>
                <span class="tag-num">{{ formatCurrency(summary.selection.total_uplift) }}</span>
              </div>
            </div>

            <div class="result__slots">
              <div v-for="slot in summary.selection.slots" :key="slot.rule_key" class="slot">
                <span class="slot__zone">{{ slot.zone }}</span>
                <span class="slot__label">{{ slot.label }}</span>
                <span class="tag-num slot__uplift">{{ formatCurrency(slot.uplift_month) }}</span>
              </div>
            </div>
            <div v-if="summary.selection.skipped.length" class="result__skip">
              冲突组剔除：{{ summary.selection.skipped.map((item) => item.label).join('、') }}
            </div>

            <div class="result__meta">
              样本 {{ summary.basket_count }} 张小票 · 客单均值 {{ formatCurrency(summary.mean_amount) }} ·
              月化系数 {{ (30 / summary.params.sample_days).toFixed(2) }} · {{ formatDuration(mining.current?.duration_ms ?? 0) }}
            </div>
          </div>
        </ShelfBand>

        <ShelfBand index="—" title="算法口径" caption="写进 README 的同一套口径">
          <dl class="facts">
            <div>
              <dt>频繁项集</dt>
              <dd>逐层候选生成 + 支持度计数 + 剪枝；min_support = {{ mining.params.min_support }}</dd>
            </div>
            <div>
              <dt>规则过滤</dt>
              <dd>lift &gt; {{ mining.params.filter_lift }} 且 confidence &gt; {{ mining.params.filter_confidence }}</dd>
            </div>
            <div>
              <dt>稳定性</dt>
              <dd>三层 lift &gt; 1.15 且 Wilson 95% 区间下界 &gt; 1</dd>
            </div>
            <div>
              <dt>预估月增量</dt>
              <dd>共现小票数 × 客单均值 × 采纳率 0.35 × (30 / 样本天数)</dd>
            </div>
            <div>
              <dt>货架位</dt>
              <dd>K=6 贪心背包：按增量排序，同冲突组只取一条</dd>
            </div>
          </dl>
        </ShelfBand>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ShelfBand from '../components/common/ShelfBand.vue'
import StatSlip, { type SlipItem } from '../components/common/StatSlip.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useMiningStore } from '../stores/miningStore'
import { useAuthStore } from '../stores/authStore'
import { CHANNEL_LABELS, RUN_STATUS_LABELS, TIER_LABELS } from '../constants/enums'
import { formatCurrency, formatDateTime, formatDuration, formatInteger, formatPercent } from '../utils/format'
import type { MiningRun } from '../types/domain'

const mining = useMiningStore()
const auth = useAuthStore()
const router = useRouter()

const sizeFilter = ref<number | undefined>(undefined)
const canRun = computed(() => auth.can('mining:run'))
const canReadBaskets = computed(() => auth.can('baskets:read'))
const dataset = computed(() => mining.dataset)
const summary = computed(() => {
  const value = mining.current?.summary
  if (!value || !('selection' in value)) return null
  return value
})

const datasetTags = computed<SlipItem[]>(() => {
  const data = dataset.value
  if (!data) {
    const run = summary.value
    return [
      { label: '小票', value: run?.basket_count ?? '—', unit: '张' },
      { label: '客单均值', value: run ? formatCurrency(run.mean_amount) : '—' },
      { label: '样本窗口', value: run?.params.sample_days ?? '—', unit: '天' },
      { label: 'POS 明细', value: '无权限', hint: '403' },
    ]
  }
  return [
    { label: '小票', value: formatInteger(data.baskets), unit: '张' },
    { label: '试点 SKU', value: data.skus, unit: '个' },
    { label: '平均行数', value: data.avg_lines.toFixed(1), unit: '行/张' },
    { label: '客单均值', value: formatCurrency(data.mean_amount), tone: 'mint' },
    { label: '门店', value: data.stores, unit: '家' },
    { label: '样本窗口', value: data.sample_days, unit: '天' },
    { label: '采纳率口径', value: `${Math.round(data.adoption_rate * 100)}%` },
  ]
})

const sizeTabs = [
  { label: '全部', value: undefined },
  { label: '1 项', value: 1 },
  { label: '2 项', value: 2 },
  { label: '3 项', value: 3 },
]

async function bootstrap() {
  if (canReadBaskets.value) {
    await mining.loadDataset()
  }
  await mining.loadRuns()
  const latest = mining.current
  if (latest?.status === 'succeeded') {
    await mining.loadItemsets(latest.id, sizeFilter.value)
  }
}

async function run() {
  try {
    await mining.runMining()
    sizeFilter.value = undefined
    await mining.loadItemsets(mining.current!.id)
  } catch {
    /* 错误已写入 store */
  }
}

async function openRun(run: MiningRun) {
  await mining.openRun(run)
}

async function changeSize(value: number | undefined) {
  sizeFilter.value = value
  if (run_id.value) {
    await mining.loadItemsets(run_id.value, value)
  }
}

const run_id = computed(() => mining.current?.id)

onMounted(bootstrap)
</script>

<style scoped>
.mining {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.notice {
  margin-top: 12px;
  border: 1px dashed var(--tag-deep);
  background: var(--tag-pale);
  padding: 8px 12px;
  font-size: 12px;
  color: oklch(40% 0.05 80);
}
.strip {
  margin-top: 14px;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}
.strip__hint {
  font-size: 10px;
  color: var(--ink-faint);
  border-left: 1px solid var(--shelf-soft);
  padding-left: 8px;
}
.columns {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(310px, 0.85fr);
  gap: 30px;
  align-items: start;
}
.col {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.col--side {
  position: sticky;
  top: 58px;
}
.params {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
}
.param {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.param__hint {
  font-size: 10px;
  color: var(--ink-faint);
}
.param--formula {
  grid-column: span 2;
  background: var(--paper-2);
  border: 1px dashed var(--shelf-soft);
  padding: 8px 10px;
  gap: 3px;
}
.param--formula code {
  font-family: var(--tag-font);
  font-size: 11px;
  color: var(--ink-soft);
}
.tabs {
  display: inline-flex;
  border: 1px solid var(--shelf-soft);
}
.tab {
  background: transparent;
  border: 0;
  border-right: 1px solid var(--shelf-soft);
  padding: 3px 9px;
  font-size: 11px;
  color: var(--ink-soft);
  cursor: pointer;
}
.tab:last-child {
  border-right: 0;
}
.tab.is-on {
  background: var(--tag-pale);
  color: var(--ink);
}
.mono {
  font-family: var(--tag-font);
  font-size: 11.5px;
  letter-spacing: 0.01em;
}
.ta-r {
  text-align: right;
}
tr.is-current td {
  background: color-mix(in oklch, var(--mint-pale) 70%, var(--paper));
}
tbody tr {
  cursor: pointer;
}
.muted {
  font-size: 12px;
  color: var(--ink-faint);
  padding: 8px 0;
}
.baskets {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(228px, 1fr));
  gap: 12px;
}
.basket {
  border: 1px solid var(--shelf-soft);
  background: var(--paper-2);
  padding: 9px 11px 8px;
  border-top: 2px solid var(--shelf-soft);
}
.basket__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.basket__meta {
  font-size: 10px;
  color: var(--ink-faint);
  margin-top: 2px;
}
.basket__lines {
  list-style: none;
  margin: 7px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11.5px;
}
.basket__lines li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px dotted var(--shelf-soft);
  padding-bottom: 2px;
}
.basket__total {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 11px;
  font-weight: 500;
}
.result {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.result__stack {
  display: flex;
  flex-direction: column;
}
.result__row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dotted var(--shelf-soft);
  font-size: 12px;
}
.result__row .tag-num {
  font-size: 16px;
  font-weight: 600;
}
.result__row--strong {
  color: var(--mint-ink);
}
.result__row--total {
  border-bottom: 0;
  border-top: 1px solid var(--shelf);
  margin-top: 2px;
  padding-top: 8px;
}
.result__row--total .tag-num {
  font-size: 20px;
}
.result__slots {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.slot {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: baseline;
  font-size: 11.5px;
  border-left: 2px solid var(--mint);
  padding: 3px 0 3px 7px;
}
.slot__zone {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.slot__uplift {
  font-weight: 600;
}
.result__skip {
  font-size: 10.5px;
  color: var(--ink-faint);
  border-top: 1px dashed var(--shelf-soft);
  padding-top: 6px;
}
.result__meta {
  font-size: 10px;
  color: var(--ink-faint);
  border-top: 1px solid var(--shelf-soft);
  padding-top: 7px;
}
.facts {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
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
@media (max-width: 1279px) {
  .columns {
    grid-template-columns: minmax(0, 1fr);
  }
  .col--side {
    position: static;
  }
}
@media (max-width: 767px) {
  .params {
    grid-template-columns: minmax(0, 1fr);
  }
  .param--formula {
    grid-column: span 1;
  }
}
</style>
