<template>
  <header class="ph">
    <div class="ph__left">
      <div v-if="eyebrow" class="eyebrow">{{ eyebrow }}</div>
      <h1 class="ph__title">{{ title }}</h1>
      <p v-if="description" class="ph__desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="ph__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; eyebrow?: string; description?: string }>()
</script>

<style scoped>
.ph {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--shelf);
}
.ph__title {
  font-size: clamp(19px, 2vw, 24px);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.01em;
  margin-top: 3px;
}
.ph__desc {
  margin-top: 5px;
  font-size: 12.5px;
  color: var(--ink-soft);
  max-width: 74ch;
}
.ph__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
@media (max-width: 767px) {
  .ph {
    align-items: flex-start;
  }
}
</style>
