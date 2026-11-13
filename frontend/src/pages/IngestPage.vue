<template>
  <div class="ingest">
    <PageHeader
      eyebrow="01 · 每日补传入库"
      title="补传核对"
      description="店长每天补传的小票按「发生时间 + 来源序号」确定唯一有效版本：重复补传不新增，作废不参与挖掘，晚到的更正只影响之后的新分析。每次导入都会留下可回放的台账。"
    >
      <template #actions>
        <button class="btn btn--quiet" type="button" :disabled="!canImport || store.working" @click="fillDemo">
          填入演示补传
        </button>
        <button
          class="btn"
          type="button"
          data-test="import-demo"
          :disabled="!canImport || store.working"
          :title="canImport ? '' : '店长账号无导入权限（后端返回 403）'"
          @click="runDemo"
        >
          {{ store.working ? '入库中…' : '运行演示批次' }}
        </button>
        <button
          class="btn btn--mint"
          type="button"
          data-test="import-submit"
          :disabled="!canImport || store.working || !parsed.records.length"
          @click="submit"
        >
          导入这批补传
        </button>
      </template>
    </PageHeader>

    <div v-if="!canImport" class="notice notice--tag">
      当前是店长账号：没有 POS 明细与补传导入权限（/api/ingest/summary 会返回 403）。补传核对由品类运营 / 品类总监操作。
    </div>
    <div v-if="store.error" class="notice notice--alert">{{ store.error }}</div>
    <div v-else-if="store.notice" class="notice notice--mint" data-test="ingest-notice">{{ store.notice }}</div>

    <div class="strip">
      <StatSlip :items="stats" />
    </div>

    <div class="columns">
      <section class="col">
        <ShelfBand
          index="01"
          title="批次逐票处置"
          :caption="`${shown?.batch_no ?? '—'} · ${shown?.file_name || '手工记录'}${shown?.batch_no === latest?.batch_no ? ' · 最近一次导入' : ' · 回放'}`"
        >
          <div v-if="!shown" class="muted">还没有补传批次。点「填入演示补传」再导入，或运行演示批次。</div>
          <div v-else class="receipt">
            <div class="receipt__head">
              <div class="receipt__stamp">
                <span class="eyebrow">intake · daily</span>
                <span class="receipt__batch mono">{{ shown.batch_no }}</span>
              </div>
              <div class="receipt__meta">
                <span>{{ shown.source === 'demo' ? '演示批次' : shown.source }}</span>
                <span>{{ formatDateTime(shown.imported_at) }}</span>
              </div>
            </div>
            <div class="tallies">
              <div v-for="row in tallyRows" :key="row.key" class="tally" :class="`tally--${row.key}`">
                <span class="tally__label">{{ row.label }}</span>
                <span class="tally__num tag-num">{{ shown.counts[row.key] ?? 0 }}</span>
                <span class="tally__hint">{{ row.hint }}</span>
              </div>
            </div>
            <table class="grid-table" data-test="ingest-records">
              <thead>
                <tr>
                  <th>#</th>
                  <th>记录号</th>
                  <th>类型</th>
                  <th>小票</th>
                  <th>发生时间</th>
                  <th>处置</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in shown.records" :key="row.record_id">
                  <td class="mono">{{ shown.records.indexOf(row) + 1 }}</td>
                  <td class="mono">{{ row.record_id }}</td>
                  <td>{{ INGEST_RECORD_TYPE_LABELS[row.record_type as IngestRecordType] ?? row.record_type }}</td>
                  <td class="mono">{{ row.basket_no }}<span v-if="row.target" class="receipt__target"> → {{ row.target }}</span></td>
                  <td class="mono">{{ formatDateTime(row.occurred_at) }}</td>
                  <td><span :class="['chip', INGEST_RESULT_TONES[row.result as IngestResult] ?? '']">{{ row.result_label }}</span></td>
                  <td class="receipt__note">{{ row.note }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </ShelfBand>

        <ShelfBand
          index="02"
          title="最终有效小票"
          :caption="`全部有效小票共 ${store.summary?.totals.final_baskets ?? 0} 张 · 下方显示最近入库的最多 200 张；作废与被取代版本不在此列`"
        >
          <div v-if="!store.finalBaskets.length" class="muted">还没有有效小票。</div>
          <table v-else class="grid-table" data-test="final-baskets">
            <thead>
              <tr>
                <th>小票</th>
                <th>版本</th>
                <th>门店</th>
                <th>发生时间</th>
                <th class="ta-r">净额</th>
                <th>明细</th>
                <th>来源批次</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="basket in store.finalBaskets" :key="basket.basket_no">
                <td class="mono">
                  {{ basket.basket_no }}
                  <span v-if="basket.version > 1" class="receipt__target">v{{ basket.version }}</span>
                </td>
                <td class="mono">v{{ basket.version }}</td>
                <td>{{ basket.store_name }}</td>
                <td class="mono">{{ formatDateTime(basket.basket_ts) }}</td>
                <td class="ta-r is-num">{{ formatCurrency(basket.net_amount) }}</td>
                <td class="receipt__lines">{{ lineText(basket.lines) }}</td>
                <td class="mono">{{ basket.source_batch }}</td>
              </tr>
            </tbody>
          </table>
        </ShelfBand>

        <ShelfBand index="03" title="补传批次台账" caption="点一行回放该批次的逐票处置结果">
          <div v-if="!store.batches.length" class="muted">还没有批次。</div>
          <table v-else class="grid-table">
            <thead>
              <tr>
                <th>批次</th>
                <th>文件 / 来源</th>
                <th class="ta-r">接收</th>
                <th class="ta-r">重复</th>
                <th class="ta-r">作废</th>
                <th class="ta-r">更正</th>
                <th class="ta-r">拒绝</th>
                <th>入库时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="batch in store.batches"
                :key="batch.batch_no"
                :class="{ 'is-current': batch.batch_no === latest?.batch_no }"
                @click="openBatch(batch.batch_no)"
              >
                <td class="mono">{{ batch.batch_no }}</td>
                <td>{{ batch.file_name || batch.source }}</td>
                <td class="ta-r is-num">{{ batch.counts.received }}</td>
                <td class="ta-r is-num">{{ batch.counts.duplicate }}</td>
                <td class="ta-r is-num">{{ batch.counts.voided }}</td>
                <td class="ta-r is-num">{{ batch.counts.corrected }}</td>
                <td class="ta-r is-num">{{ batch.counts.rejected }}</td>
                <td class="mono">{{ formatDateTime(batch.imported_at) }}</td>
              </tr>
            </tbody>
          </table>
        </ShelfBand>
      </section>

      <aside class="col col--side">
        <ShelfBand index="—" title="待导入记录" caption="编辑 JSON 后点「导入这批补传」；字段口径见下方">
          <label class="param">
            <span class="label">批次号 batch_no</span>
            <input v-model="batchNo" class="field mono" type="text" data-test="ingest-batch-no" />
          </label>
          <label class="param">
            <span class="label">文件名（可空）</span>
            <input v-model="fileName" class="field" type="text" placeholder="supplement-2026-11-13.json" />
          </label>
          <label class="param">
            <span class="label">记录（JSON 数组）</span>
            <textarea v-model="recordsText" class="field mono area" rows="16" spellcheck="false" data-test="ingest-records-input" />
          </label>
          <div class="parsed" :class="{ 'parsed--bad': parsed.error }">
            <span v-if="parsed.error" class="parsed__bad">JSON 解析失败：{{ parsed.error }}</span>
            <span v-else>
              已解析 <strong>{{ parsed.records.length }}</strong> 条记录 ·
              补传 {{ parsed.kinds.supplement }} · 作废 {{ parsed.kinds.void }} · 更正 {{ parsed.kinds.correction }}
            </span>
          </div>
        </ShelfBand>

        <ShelfBand index="—" title="入库口径" caption="写进 README 的同一套口径">
          <dl class="facts">
            <div>
              <dt>唯一有效内容</dt>
              <dd>按 (occurred_at, source_seq, 到达序号) 排序；同票同内容判重复，不新增版本。</dd>
            </div>
            <div>
              <dt>作废</dt>
              <dd>作废先到 / 后到都成立：该票没有有效版本，不进入挖掘；作废后补传的原票也不生效。</dd>
            </div>
            <div>
              <dt>更正</dt>
              <dd>必须声明 same_as_no；生成新版本并取代旧版本，晚到更正只影响之后的新分析。</dd>
            </div>
            <div>
              <dt>拒绝</dt>
              <dd>未知 SKU / 数量非正 / 金额为负 / 缺发生时间 / 企图用补传直接覆盖旧内容。</dd>
            </div>
            <div>
              <dt>已发布建议单</dt>
              <dd>绑定生成时的批次与有效版本口径，不回写；后续补传只在新增分析里生效。</dd>
            </div>
          </dl>
        </ShelfBand>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ShelfBand from '../components/common/ShelfBand.vue'
import StatSlip, { type SlipItem } from '../components/common/StatSlip.vue'
import { useIngestStore } from '../stores/ingestStore'
import { useAuthStore } from '../stores/authStore'
import { INGEST_RECORD_TYPE_LABELS, INGEST_RESULT_TONES, type IngestRecordType, type IngestResult } from '../constants/ingest'
import { formatCurrency, formatDateTime, formatInteger } from '../utils/format'
import type { IngestFinalBasket } from '../types/domain'

const store = useIngestStore()
const auth = useAuthStore()
const canImport = computed(() => auth.can('baskets:import'))

const tallyRows: Array<{ key: IngestResult; label: string; hint: string }> = [
  { key: 'received', label: '接收', hint: '新增有效版本' },
  { key: 'duplicate', label: '重复', hint: '内容一致，不新增' },
  { key: 'voided', label: '作废', hint: '不参与挖掘' },
  { key: 'corrected', label: '更正', hint: '取代旧版本' },
  { key: 'rejected', label: '拒绝', hint: '字段不合法' },
]

const stats = computed<SlipItem[]>(() => {
  const summary = store.summary
  const totals = summary?.totals
  return [
    { label: '最终有效小票', value: totals?.final_baskets ?? '—', unit: '张', tone: 'mint' },
    { label: '本次接收', value: summary?.last_counts.received ?? 0, unit: '条' },
    { label: '本次拒绝', value: summary?.last_counts.rejected ?? 0, unit: '条' },
    { label: '已作废小票', value: totals?.baskets_voided ?? 0, unit: '张' },
    { label: '有更正的小票', value: totals?.baskets_with_corrections ?? 0, unit: '张' },
    { label: '导入批次', value: totals?.ledger_batches ?? 0, unit: '批' },
  ]
})

const latest = computed(() => store.latest)
const shown = computed(() => store.selected ?? store.latest)

const batchNo = ref(`ING-${new Date().toISOString().slice(0, 10)}-UI-${String(Math.floor(Math.random() * 9000) + 1000)}`)
const fileName = ref('supplement-2026-11-13.json')
const recordsText = ref(defaultRecords())

function defaultRecords(): string {
  const basket = store.finalBaskets[0]
  const demoLines = [
    { sku: 'N01', qty: 1, amount: 15.72 },
    { sku: 'N02', qty: 1, amount: 7.14 },
  ]
  return JSON.stringify(
    [
      {
        record_id: 'SUP-0001',
        record_type: 'supplement',
        basket_no: 'BR-DEMO-0001',
        occurred_at: '2026-10-11T12:30:00+08:00',
        source_seq: 1,
        store_code: basket?.store_code ?? 'S09',
        store_name: basket?.store_name ?? '拾光便利·临港二店',
        store_tier: basket?.store_tier ?? 'low',
        channel: 'pos',
        lines: demoLines,
      },
      {
        record_id: 'SUP-0002',
        record_type: 'supplement',
        basket_no: 'BR-DEMO-0001',
        occurred_at: '2026-10-11T12:30:00+08:00',
        source_seq: 2,
        store_code: basket?.store_code ?? 'S09',
        store_name: basket?.store_name ?? '拾光便利·临港二店',
        store_tier: basket?.store_tier ?? 'low',
        channel: 'pos',
        lines: demoLines,
      },
      {
        record_id: 'VOID-0001',
        record_type: 'void',
        basket_no: 'BR-DEMO-0002',
        occurred_at: '2026-10-11T13:10:00+08:00',
        source_seq: 3,
        reason: '收银机重复结算',
      },
      {
        record_id: 'COR-0001',
        record_type: 'correction',
        basket_no: 'BR-DEMO-0001X',
        same_as_no: 'BR-DEMO-0001',
        occurred_at: '2026-10-11T12:30:00+08:00',
        source_seq: 4,
        store_code: basket?.store_code ?? 'S09',
        store_name: basket?.store_name ?? '拾光便利·临港二店',
        store_tier: basket?.store_tier ?? 'low',
        channel: 'pos',
        lines: [
          { sku: 'N01', qty: 2, amount: 31.44 },
          { sku: 'N02', qty: 1, amount: 7.14 },
        ],
      },
      {
        record_id: 'REJ-0001',
        record_type: 'supplement',
        basket_no: 'BR-DEMO-0003',
        occurred_at: '2026-10-11T14:20:00+08:00',
        source_seq: 5,
        store_code: basket?.store_code ?? 'S09',
        store_name: basket?.store_name ?? '拾光便利·临港二店',
        store_tier: 'low',
        channel: 'pos',
        lines: [{ sku: 'ZZZ999', qty: 1, amount: 9.9 }],
      },
    ],
    null,
    2,
  )
}

const parsed = computed(() => {
  try {
    const value = JSON.parse(recordsText.value)
    if (!Array.isArray(value)) {
      return { records: [], kinds: { supplement: 0, void: 0, correction: 0 }, error: '需要 JSON 数组' }
    }
    const kinds = { supplement: 0, void: 0, correction: 0 }
    for (const item of value) {
      const type = (item?.record_type ?? '') as IngestRecordType
      if (type in kinds) kinds[type] += 1
    }
    return { records: value, kinds, error: '' }
  } catch (error) {
    return {
      records: [],
      kinds: { supplement: 0, void: 0, correction: 0 },
      error: (error as Error).message,
    }
  }
})

function fillDemo() {
  recordsText.value = defaultRecords()
  batchNo.value = `ING-${new Date().toISOString().slice(0, 10)}-UI-${String(Math.floor(Math.random() * 9000) + 1000)}`
}

async function submit() {
  if (parsed.value.error || !parsed.value.records.length) return
  try {
    await store.submit({
      batch_no: batchNo.value.trim(),
      file_name: fileName.value.trim(),
      source: 'manual',
      note: '导入页手工提交',
      records: parsed.value.records,
    })
  } catch {
    /* store 已记录 */
  }
}

async function runDemo() {
  try {
    await store.loadDemo()
  } catch {
    /* store 已记录 */
  }
}

async function openBatch(batchNoValue: string) {
  await store.openBatch(batchNoValue)
}

function lineText(lines: IngestFinalBasket['lines']): string {
  return lines.map((line) => `${line.sku}×${line.qty}`).join(' · ')
}

onMounted(async () => {
  await store.load()
})
</script>

<style scoped>
.ingest {
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
.columns {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.85fr);
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
.receipt {
  border: 1px solid var(--shelf);
  background: var(--paper-2);
}
.receipt__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  padding: 9px 12px 8px;
  background: var(--mint);
  color: var(--mint-ink);
  border-bottom: 2px solid var(--mint-deep);
}
.receipt__stamp {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.receipt__stamp .eyebrow {
  color: var(--mint-ink);
  opacity: 0.75;
}
.receipt__batch {
  font-size: 15px;
  font-weight: 600;
}
.receipt__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  font-size: 10.5px;
  opacity: 0.85;
}
.tallies {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border-bottom: 1px solid var(--shelf-soft);
}
.tally {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 9px 10px 8px;
  border-right: 1px dotted var(--shelf-soft);
}
.tally:last-child {
  border-right: 0;
}
.tally--received {
  background: color-mix(in oklch, var(--mint-pale) 55%, var(--paper));
}
.tally--voided,
.tally--rejected {
  background: color-mix(in oklch, var(--alert-pale) 45%, var(--paper));
}
.tally__label {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.tally__num {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.1;
}
.tally__hint {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.receipt__note {
  font-size: 11px;
  color: var(--ink-soft);
}
.receipt__target {
  margin-left: 4px;
  color: var(--tag-deep);
  font-size: 10px;
}
.receipt__lines {
  font-family: var(--tag-font);
  font-size: 10.5px;
  color: var(--ink-soft);
}
.ta-r {
  text-align: right;
}
.mono {
  font-family: var(--tag-font);
  font-size: 11.5px;
  letter-spacing: 0.01em;
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
.param {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}
.area {
  min-height: 240px;
  resize: vertical;
  line-height: 1.45;
}
.parsed {
  font-size: 11px;
  color: var(--ink-soft);
  border-top: 1px dashed var(--shelf-soft);
  padding-top: 7px;
}
.parsed__bad {
  color: var(--alert);
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
  .tallies {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
