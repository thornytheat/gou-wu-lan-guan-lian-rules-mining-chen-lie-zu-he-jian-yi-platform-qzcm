import { ref } from 'vue'

export interface ToastItem {
  id: number
  text: string
  tone: 'mint' | 'tag' | 'alert'
}

let counter = 0

/** 轻量提示条：3 秒自动消失，错误可手动关闭（错误态可恢复）。 */
export function useToast() {
  const items = ref<ToastItem[]>([])

  function push(text: string, tone: ToastItem['tone'] = 'mint') {
    const id = ++counter
    items.value = [...items.value, { id, text, tone }]
    window.setTimeout(() => {
      items.value = items.value.filter((item) => item.id !== id)
    }, 3200)
  }

  function dismiss(id: number) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  return { items, push, dismiss }
}
