<template>
  <div class="empty">
    <div class="empty__pegs">
      <span v-for="index in 4" :key="index" class="empty__peg" />
    </div>
    <div class="empty__body">
      <div class="empty__title">{{ title }}</div>
      <p class="empty__hint">{{ hint }}</p>
      <div v-if="$slots.action" class="empty__action">
        <slot name="action" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; hint: string }>()
</script>

<style scoped>
.empty {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  border: 1px dashed var(--shelf);
  padding: 22px 20px;
  background: var(--paper-2);
}
.empty__pegs {
  display: flex;
  gap: 8px;
  padding-left: 4px;
}
.empty__peg {
  width: 9px;
  height: 52px;
  border: 1px solid var(--shelf-soft);
  background: var(--paper-3);
}
.empty__peg:nth-child(2) {
  height: 64px;
  margin-top: -6px;
}
.empty__title {
  font-size: 14px;
  font-weight: 500;
}
.empty__hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink-soft);
  max-width: 70ch;
}
.empty__action {
  margin-top: 10px;
}
@media (max-width: 767px) {
  .empty {
    grid-template-columns: minmax(0, 1fr);
  }
  .empty__pegs {
    display: none;
  }
}
</style>
