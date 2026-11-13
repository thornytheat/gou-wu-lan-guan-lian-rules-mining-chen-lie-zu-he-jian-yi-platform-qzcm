<template>
  <section class="band">
    <div class="band__head">
      <div class="band__title-wrap">
        <span v-if="index" class="band__index">{{ index }}</span>
        <h2 class="band__title">{{ title }}</h2>
        <span v-if="caption" class="band__caption">{{ caption }}</span>
      </div>
      <div v-if="$slots.actions" class="band__actions">
        <slot name="actions" />
      </div>
    </div>
    <div class="band__body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ title: string; index?: string; caption?: string }>()
</script>

<style scoped>
.band {
  position: relative;
  border-top: var(--shelf-line);
  padding-top: 12px;
  margin-top: 24px;
}
.band::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 8px;
  background: linear-gradient(180deg, oklch(55% 0.02 76 / 0.14), transparent);
  pointer-events: none;
}
.band__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.band__title-wrap {
  display: flex;
  align-items: baseline;
  gap: 9px;
  flex-wrap: wrap;
}
.band__index {
  font-family: var(--tag-font);
  font-size: 10.5px;
  font-weight: 600;
  color: var(--tag-deep);
  border: 1px solid var(--tag-deep);
  padding: 1px 5px;
}
.band__title {
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.band__caption {
  font-size: 11px;
  color: var(--ink-faint);
}
.band__actions {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
