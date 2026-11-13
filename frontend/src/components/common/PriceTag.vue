<template>
  <div class="tag" :class="[tone === 'mint' ? 'tag--mint' : '', compact ? 'tag--compact' : '']">
    <span class="tag__label">{{ label }}</span>
    <span class="tag__value">
      <span class="tag__num">{{ value }}</span>
      <span v-if="unit" class="tag__unit">{{ unit }}</span>
    </span>
    <span v-if="hint" class="tag__hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{ label: string; value: string | number; unit?: string; hint?: string; tone?: 'tag' | 'mint'; compact?: boolean }>(),
  { unit: '', hint: '', tone: 'tag' },
)
</script>

<style scoped>
.tag {
  display: inline-flex;
  flex-direction: column;
  gap: 1px;
  background: var(--tag-pale);
  border: 1px dashed var(--tag-deep);
  padding: 7px 11px 6px;
  min-width: 104px;
  transform: rotate(-0.5deg);
  box-shadow: 1px 2px 0 oklch(70% 0.05 88 / 0.28);
}
.tag--mint {
  background: var(--mint-pale);
  border-color: var(--mint-deep);
  box-shadow: 1px 2px 0 oklch(60% 0.05 168 / 0.26);
}
.tag--compact {
  min-width: 0;
  padding: 4px 8px 3px;
}
.tag__label {
  font-size: 9.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.tag__value {
  display: flex;
  align-items: baseline;
  gap: 3px;
}
.tag__num {
  font-family: var(--tag-font);
  font-size: 21px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  letter-spacing: -0.02em;
}
.tag--compact .tag__num {
  font-size: 15px;
}
.tag__unit {
  font-size: 10.5px;
  color: var(--ink-soft);
}
.tag__hint {
  font-size: 9.5px;
  color: var(--ink-faint);
}
</style>
