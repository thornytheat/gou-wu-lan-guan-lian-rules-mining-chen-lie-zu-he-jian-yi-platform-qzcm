<template>
  <div class="detail">
    <div class="detail__back">
      <RouterLink class="btn btn--quiet btn--sm" to="/rules">← 返回规则列表</RouterLink>
    </div>

    <ErrorNotice v-if="rules.error" :message="rules.error" @retry="load" />

    <div v-if="!rule" class="muted">加载中…</div>
    <template v-else>
      <PageHeader eyebrow="规则详情 · 共现矩阵 / 分层对照 / 反例" :title="`${rule.antecedent_labels.join(' + ')} → ${rule.consequent_labels.join(' + ')}`">
        <template #actions>
          <span :class="['chip', rule.stable ? 'chip--mint' : 'chip--tag']">
            {{ rule.stable ? '三层稳定' : '观察' }}
          </span>
          <span :class="['chip', rule.status === 'adopted' ? 'chip--mint' : rule.status === 'rejected' ? 'chip--alert' : '']">
            {{ RULE_STATUS_LABELS[rule.status] }}
          </span>
          <span class="chip">{{ rule.zone }}</span>
        </template>
      </PageHeader>

      <div class="strip">
        <StatSlip :items="metrics" />
      </div>

      <div class="columns">
        <section class="col">
          <ShelfBand index="01" title="门店分层稳定性" caption="高 / 中 / 低客流各 1,000 张小票">
            <TierBar v-if="rule.tier_detail.length" :tiers="rule.tier_detail" />
            <div v-else class="muted">该批次没有分层数据。</div>
            <table class="grid-table tier-table">
              <thead>
                <tr>
                  <th>分层</th>
                  <th class="ta-r">小票数</th>
                  <th class="ta-r">共现</th>
                  <th class="ta-r">lift</th>
                  <th class="ta-r">CI 下界</th>
                  <th>结论</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tier in rule.tier_detail" :key="tier.tier">
                  <td>{{ TIER_LABELS[tier.tier] }}</td>
                  <td class="ta-r is-num">{{ tier.baskets }}</td>
                  <td class="ta-r is-num">{{ tier.cooccur }}</td>
                  <td class="ta-r is-num">{{ tier.lift.toFixed(2) }}</td>
                  <td class="ta-r is-num">{{ tier.ci_low.toFixed(2) }}</td>
                  <td>
                    <span :class="['chip', tier.stable ? 'chip--mint' : 'chip--tag']">
                      {{ tier.stable ? '稳定' : '观察' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </ShelfBand>

          <ShelfBand index="02" title="共现矩阵" caption="规则两端 SKU 用价签黄描边标出">
            <MatrixHeat
              :skus="rule.matrix.skus"
              :matrix="rule.matrix.matrix"
              :highlight="[...rule.antecedent, ...rule.consequent]"
            />
          </ShelfBand>

          <ShelfBand index="03" title="反例小票" :caption="`含前项但不含后项：${rule.counterexample_count} 张（展示最近 ${rule.counterexamples.length} 张）`">
            <div v-if="!rule.counterexamples.length" class="muted">没有反例小票。</div>
            <div v-else class="counter">
              <article v-for="basket in rule.counterexamples" :key="basket.id" class="counter__row">
                <div class="counter__head">
                  <span class="mono">{{ basket.basket_no }}</span>
                  <span class="chip">{{ TIER_LABELS[basket.store_tier] }}</span>
                  <span class="tag-num">{{ formatCurrency(basket.net_amount) }}</span>
                </div>
                <div class="counter__lines">
                  {{ basket.lines.map((line) => line.name).join(' · ') }}
                </div>
              </article>
            </div>
          </ShelfBand>
        </section>

        <aside class="col col--side">
          <ShelfBand index="—" title="增量口径" caption="与 README 一致的公式">
            <div class="basis">
              <div class="basis__formula">{{ rule.uplift_basis.formula }}</div>
              <dl class="basis__rows">
                <div>
                  <dt>共现小票数</dt>
                  <dd class="tag-num">{{ rule.uplift_basis.cooccur_count }}</dd>
                </div>
                <div>
                  <dt>客单均值</dt>
                  <dd class="tag-num">{{ formatCurrency(rule.uplift_basis.mean_amount ?? 0) }}</dd>
                </div>
                <div>
                  <dt>采纳率</dt>
                  <dd class="tag-num">{{ (rule.uplift_basis.adoption_rate ?? 0.35).toFixed(2) }}</dd>
                </div>
                <div>
                  <dt>月化系数</dt>
                  <dd class="tag-num">{{ rule.uplift_basis.monthly_factor.toFixed(2) }}</dd>
                </div>
                <div class="basis__total">
                  <dt>预估月增量</dt>
                  <dd class="tag-num">{{ formatCurrency(rule.uplift_month) }}</dd>
                </div>
              </dl>
            </div>
          </ShelfBand>

          <ShelfBand index="—" title="复核" caption="采纳 / 挂起 / 驳回都会写入审计日志">
            <div v-if="!canReview" class="muted">{{ MESSAGES.viewerHint }}</div>
            <template v-else>
              <textarea
                v-model="reason"
                class="field reason"
                rows="3"
                placeholder="复核理由（驳回 / 挂起必填）：例如「三层 lift 稳定，但端架 A 已有啤酒组合，先挂起」"
              />
              <div class="review-actions">
                <button class="btn btn--mint btn--sm" type="button" :disabled="working" @click="decide('adopt')">采纳</button>
                <button class="btn btn--sm" type="button" :disabled="working" @click="decide('park')">挂起</button>
                <button class="btn btn--sm" type="button" :disabled="working" @click="decide('reject')">驳回</button>
              </div>
              <div v-if="localError" class="review-error">{{ localError }}</div>
              <div v-if="rules.notice" class="review-ok">{{ rules.notice }}</div>
            </template>

            <div class="history">
              <div class="label">复核记录</div>
              <div v-if="!rule.reviews?.length" class="muted">还没有复核记录。</div>
              <ul v-else class="history__list">
                <li v-for="review in rule.reviews" :key="review.id">
                  <span :class="['chip', review.decision === 'adopt' ? 'chip--mint' : review.decision === 'reject' ? 'chip--alert' : 'chip--tag']">
                    {{ REVIEW_DECISION_LABELS[review.decision] }}
                  </span>
                  <span class="history__who">{{ review.reviewer }}</span>
                  <span class="history__when">{{ formatDateTime(review.reviewed_at) }}</span>
                  <p v-if="review.reason" class="history__reason">{{ review.reason }}</p>
                </li>
              </ul>
            </div>
          </ShelfBand>

          <ShelfBand index="—" title="去向" caption="采纳后进入陈列建议">
            <div class="next">
              <p>本规则属于冲突组 <b>{{ rule.conflict_group }}</b>；同类只有一个货架位，增量更高的那条会进入建议单。</p>
              <RouterLink class="btn btn--sm" to="/planogram">查看陈列建议</RouterLink>
            </div>
          </ShelfBand>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ShelfBand from '../components/common/ShelfBand.vue'
import StatSlip, { type SlipItem } from '../components/common/StatSlip.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import TierBar from '../components/common/TierBar.vue'
import MatrixHeat from '../components/common/MatrixHeat.vue'
import { useRuleStore } from '../stores/ruleStore'
import { useAuthStore } from '../stores/authStore'
import { MESSAGES } from '../constants/messages'
import { REVIEW_DECISION_LABELS, RULE_STATUS_LABELS, TIER_LABELS } from '../constants/enums'
import { formatCurrency, formatDateTime, formatPercent } from '../utils/format'

const route = useRoute()
const rules = useRuleStore()
const auth = useAuthStore()

const reason = ref('')
const working = ref(false)
const localError = ref('')
const rule = computed(() => rules.detail)
const canReview = computed(() => auth.can('rules:review'))

const metrics = computed<SlipItem[]>(() => {
  const row = rule.value
  if (!row) return []
  return [
    { label: '支持度', value: formatPercent(row.support), hint: `${row.cooccur_count} 张小票` },
    { label: '置信度', value: formatPercent(row.confidence) },
    { label: '提升度 lift', value: row.lift.toFixed(2), tone: 'mint', hint: `conviction ${row.conviction.toFixed(2)}` },
    {
      label: 'lift 95% CI',
      value: `${row.ci_low?.toFixed(2)}–${row.ci_high?.toFixed(2)}`,
      hint: 'Wilson 区间（共现比例）',
    },
    { label: '反例小票', value: row.counterexample_count, unit: '张' },
    { label: '预估月增量', value: formatCurrency(row.uplift_month), tone: 'mint' },
  ]
})

async function load() {
  await rules.open(route.params.id as string)
}

async function decide(decision: 'adopt' | 'reject' | 'park') {
  if ((decision === 'reject' || decision === 'park') && !reason.value.trim()) {
    localError.value = '驳回或挂起需要填写理由'
    return
  }
  localError.value = ''
  working.value = true
  try {
    await rules.decide(route.params.id as string, decision, reason.value)
    reason.value = ''
  } catch (error) {
    localError.value = (error as Error).message
  } finally {
    working.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.detail__back {
  margin-bottom: 10px;
}
.muted {
  font-size: 12px;
  color: var(--ink-faint);
  padding: 6px 0;
}
.strip {
  margin-top: 14px;
}
.columns {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.82fr);
  gap: 28px;
  align-items: start;
}
.col {
  min-width: 0;
}
.col--side {
  position: sticky;
  top: 58px;
}
.ta-r {
  text-align: right;
}
.tier-table {
  margin-top: 10px;
  font-size: 11.5px;
}
.counter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.counter__row {
  border-left: 2px solid var(--shelf);
  padding: 5px 0 5px 9px;
}
.counter__head {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 11px;
}
.counter__lines {
  font-size: 11.5px;
  color: var(--ink-soft);
  margin-top: 2px;
}
.mono {
  font-family: var(--tag-font);
  font-size: 11px;
}
.basis__formula {
  font-size: 11px;
  color: var(--ink-soft);
  border-bottom: 1px dashed var(--shelf-soft);
  padding-bottom: 7px;
}
.basis__rows {
  margin: 8px 0 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.basis__rows > div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 11.5px;
}
.basis__rows dt {
  color: var(--ink-faint);
}
.basis__rows dd {
  margin: 0;
  font-weight: 600;
}
.basis__total {
  border-top: 1px solid var(--shelf);
  padding-top: 6px;
}
.basis__total dd {
  font-size: 17px;
}
.reason {
  resize: vertical;
}
.review-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.review-error {
  margin-top: 6px;
  font-size: 11.5px;
  color: var(--alert);
}
.review-ok {
  margin-top: 6px;
  font-size: 11.5px;
  color: var(--mint-ink);
}
.history {
  margin-top: 14px;
  border-top: 1px dashed var(--shelf-soft);
  padding-top: 10px;
}
.history__list {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.history__who {
  font-size: 11px;
  margin-left: 6px;
}
.history__when {
  font-size: 10px;
  color: var(--ink-faint);
  margin-left: 6px;
}
.history__reason {
  font-size: 11px;
  color: var(--ink-soft);
  margin-top: 3px;
}
.next p {
  font-size: 11.5px;
  color: var(--ink-soft);
  margin-bottom: 8px;
}
@media (max-width: 1279px) {
  .columns {
    grid-template-columns: minmax(0, 1fr);
  }
  .col--side {
    position: static;
  }
}
</style>
