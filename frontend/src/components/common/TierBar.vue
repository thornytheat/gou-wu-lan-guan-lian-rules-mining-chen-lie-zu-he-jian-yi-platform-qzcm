<template>
  <figure class="tier">
    <figcaption class="tier__cap">
      门店分层 lift 与 95% Wilson 区间
      <span class="tier__legend">虚线 = 1.15 稳定阈值 / 实线 = lift 1.0</span>
    </figcaption>
    <svg viewBox="0 0 480 150" role="img" aria-label="门店分层 lift 与置信区间">
      <g v-for="(row, index) in rows" :key="row.tier">
        <text :x="0" :y="row.y + 10" class="tier__label">{{ TIER_LABELS[row.tier] }}</text>
        <line :x1="88" :y1="row.y + 6" :x2="392" :y2="row.y + 6" class="tier__track" />
        <rect
          :x="88"
          :y="row.y"
          :width="Math.max(2, x(row.lift) - 88)"
          height="12"
          class="tier__bar"
          :class="row.stable ? 'is-stable' : 'is-watch'"
        />
        <g class="tier__ci">
          <line :x1="x(row.ci_low)" :y1="row.y - 3" :x2="x(row.ci_low)" :y2="row.y + 15" />
          <line :x1="x(row.ci_high)" :y1="row.y - 3" :x2="x(row.ci_high)" :y2="row.y + 15" />
          <line :x1="x(row.ci_low)" :y1="row.y + 6" :x2="x(row.ci_high)" :y2="row.y + 6" />
        </g>
        <text :x="Math.min(430, x(row.ci_high) + 8)" :y="row.y + 10" class="tier__val">
          {{ row.lift.toFixed(2) }}
        </text>
        <text :x="x(row.ci_high) + 2" :y="row.y - 6" class="tier__ci-low">
          CI ≥ {{ row.ci_low.toFixed(2) }}
        </text>
      </g>
      <line :x1="x(1)" :y1="8" :x2="x(1)" :y2="138" class="tier__ref" />
      <line :x1="x(1.15)" :y1="8" :x2="x(1.15)" :y2="138" class="tier__ref tier__ref--dash" />
      <text :x="x(1.15) + 3" y="148" class="tier__tick">1.15</text>
      <text :x="x(1) + 3" y="148" class="tier__tick">1.00</text>
    </svg>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TIER_LABELS, type StoreTier } from '../../constants/enums'
import type { TierDetail } from '../../types/domain'

const props = defineProps<{ tiers: TierDetail[]; max?: number }>()

const DOMAIN_START = 0.9
const rows = computed(() =>
  props.tiers.map((tier, index) => ({
    ...tier,
    y: 12 + index * 42,
  })),
)
const domainEnd = computed(() => {
  const highest = Math.max(
    props.max ?? 2.4,
    ...rows.value.map((row) => row.ci_high || 0),
    1.2,
  )
  return Math.ceil(highest * 4) / 4
})

function x(value: number): number {
  const clamped = Math.max(DOMAIN_START, Math.min(domainEnd.value, value))
  const ratio = (clamped - DOMAIN_START) / (domainEnd.value - DOMAIN_START)
  return 88 + ratio * 304
}

export type { StoreTier }
</script>

<style scoped>
.tier {
  margin: 0;
}
.tier__cap {
  font-size: 11px;
  color: var(--ink-soft);
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.tier__legend {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.tier__label {
  font-size: 10.5px;
  fill: var(--ink-soft);
}
.tier__track {
  stroke: var(--paper-4);
  stroke-width: 12;
  stroke-linecap: butt;
}
.tier__bar.is-stable {
  fill: var(--mint);
}
.tier__bar.is-watch {
  fill: var(--tag);
}
.tier__ci line {
  stroke: var(--shelf-dark);
  stroke-width: 1.2;
}
.tier__val {
  font-family: var(--tag-font);
  font-size: 11px;
  font-weight: 600;
  fill: var(--ink);
}
.tier__ci-low {
  font-family: var(--tag-font);
  font-size: 9px;
  fill: var(--ink-faint);
}
.tier__ref {
  stroke: var(--shelf);
  stroke-width: 1;
}
.tier__ref--dash {
  stroke: var(--mint-deep);
  stroke-dasharray: 3 3;
}
.tier__tick {
  font-family: var(--tag-font);
  font-size: 9px;
  fill: var(--ink-faint);
}
</style>
