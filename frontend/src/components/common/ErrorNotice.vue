<template>
  <div class="err" role="alert">
    <div class="err__bar" />
    <div class="err__body">
      <div class="err__title">{{ title }}</div>
      <p class="err__msg">{{ message }}</p>
      <div class="err__actions">
        <button v-if="retryLabel" class="btn btn--sm" type="button" @click="$emit('retry')">
          {{ retryLabel }}
        </button>
        <slot name="action" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{ message: string; title?: string; retryLabel?: string }>(),
  { title: '这一步没跑通', retryLabel: '重试' },
)
defineEmits<{ retry: [] }>()
</script>

<style scoped>
.err {
  display: flex;
  gap: 12px;
  border: 1px solid var(--alert);
  background: var(--alert-pale);
  padding: 12px 14px;
}
.err__bar {
  width: 3px;
  background: var(--alert);
  flex: none;
}
.err__title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--alert);
}
.err__msg {
  margin-top: 3px;
  font-size: 12px;
  color: var(--ink-soft);
  max-width: 80ch;
}
.err__actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>
