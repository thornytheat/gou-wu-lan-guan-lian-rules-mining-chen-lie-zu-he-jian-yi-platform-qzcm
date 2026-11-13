<template>
  <figure class="heat">
    <figcaption class="heat__cap">
      共现矩阵（Top {{ skus.length }} SKU，单位：小票数）
      <span class="heat__legend">
        <i class="heat__scale" /> 深 = 共现多
      </span>
    </figcaption>
    <svg :viewBox="`0 0 ${size} ${size + 54}`" role="img" aria-label="SKU 共现矩阵">
      <g>
        <rect
          v-for="(cell, index) in cells"
          :key="index"
          :x="cell.x"
          :y="cell.y"
          :width="cellSize - 1"
          :height="cellSize - 1"
          :fill="cell.fill"
          :class="{ 'is-hot': cell.hot }"
        >
          <title>{{ cell.tip }}</title>
        </rect>
        <text
          v-for="(label, index) in rowLabels"
          :key="`r${index}`"
          :x="cellSize + 2"
          :y="cellSize + index * cellSize + cellSize / 2 + 3"
          class="heat__row"
        >
          {{ label }}
        </text>
        <text
          v-for="(label, index) in colLabels"
          :key="`c${index}`"
          :x="cellSize + index * cellSize + cellSize / 2"
          :y="cellSize / 2 - 18"
          class="heat__col"
          :transform="`rotate(-42 ${cellSize + index * cellSize + cellSize / 2} ${cellSize / 2 - 18})`"
        >
          {{ label }}
        </text>
      </g>
    </svg>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface MatrixSku {
  sku: string
  name: string
  category: string
  baskets: number
}

const props = defineProps<{
  skus: MatrixSku[]
  matrix: number[][]
  highlight?: string[]
}>()

const cellSize = 40
const size = computed(() => cellSize + props.skus.length * cellSize + 96)
const maxValue = computed(() => Math.max(...props.matrix.flat(), 1))

const rowLabels = computed(() => props.skus.map((item) => shortName(item.name)))
const colLabels = computed(() => props.skus.map((item) => shortName(item.name)))

function shortName(name: string): string {
  return name.replace(/\s.*$/, '').slice(0, 6)
}

const cells = computed(() => {
  const highlight = new Set(props.highlight ?? [])
  const out: Array<{ x: number; y: number; fill: string; hot: boolean; tip: string }> = []
  props.matrix.forEach((row, rowIndex) => {
    row.forEach((value, colIndex) => {
      const ratio = Math.pow(value / maxValue.value, 0.6)
      const fill =
        rowIndex === colIndex
          ? `oklch(92% ${0.03 + ratio * 0.05} 96)`
          : `oklch(${93 - ratio * 34}% ${0.03 + ratio * 0.09} 168)`
      const hot =
        highlight.size > 0 &&
        highlight.has(props.skus[rowIndex]?.sku) &&
        highlight.has(props.skus[colIndex]?.sku)
      out.push({
        x: cellSize + colIndex * cellSize,
        y: cellSize + rowIndex * cellSize,
        fill,
        hot,
        tip: `${props.skus[rowIndex]?.name} × ${props.skus[colIndex]?.name}：${value} 张`,
      })
    })
  })
  return out
})
</script>

<style scoped>
.heat {
  margin: 0;
  overflow-x: auto;
}
.heat__cap {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 11px;
  color: var(--ink-soft);
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.heat__legend {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.heat__scale {
  width: 34px;
  height: 7px;
  background: linear-gradient(90deg, oklch(93% 0.03 168), oklch(59% 0.12 168));
  display: inline-block;
}
.heat svg {
  width: 100%;
  max-width: 560px;
  height: auto;
}
.heat__row {
  font-size: 9px;
  fill: var(--ink-soft);
}
.heat__col {
  font-size: 9px;
  fill: var(--ink-soft);
}
.is-hot {
  stroke: var(--tag-deep);
  stroke-width: 1.6;
}
</style>
