import { ref, type Ref } from 'vue'

/** 统一的异步动作包装：loading / error / data，错误可恢复（retry 复用同一动作）。 */
export function useAsync<T>(action: () => Promise<T>, options: { immediate?: boolean } = {}) {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref('')
  let lastAction: (() => Promise<T>) | null = action

  async function run(next?: () => Promise<T>): Promise<T | null> {
    const job = next ?? lastAction
    if (!job) return null
    lastAction = job
    loading.value = true
    error.value = ''
    try {
      const result = await job()
      data.value = result
      return result
    } catch (err) {
      error.value = (err as Error).message ?? '操作失败'
      return null
    } finally {
      loading.value = false
    }
  }

  if (options.immediate) {
    void run()
  }

  return { data, loading, error, run }
}
