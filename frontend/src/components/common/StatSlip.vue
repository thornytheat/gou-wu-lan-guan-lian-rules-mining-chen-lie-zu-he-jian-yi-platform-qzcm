<template>
  <div class="slip">
    <PriceTag
      v-for="item in items"
      :key="item.label"
      :label="item.label"
      :value="item.value"
      :unit="item.unit"
      :hint="item.hint"
      :tone="item.tone ?? 'tag'"
      :compact="compact"
    />
  </div>
</template>

<script setup lang="ts">
import PriceTag from './PriceTag.vue'

export interface SlipItem {
  label: string
  value: string | number
  unit?: string
  hint?: string
  tone?: 'tag' | 'mint'
}

withDefaults(defineProps<{ items: SlipItem[]; compact?: boolean }>(), { compact: false })
</script>

<style scoped>
.slip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: stretch;
}
</style>
