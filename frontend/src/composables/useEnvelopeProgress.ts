import { computed, type Ref, type ComputedRef } from 'vue'
import type { Envelope } from '@/types'

export function useEnvelopeProgress(envelope: Ref<Envelope> | ComputedRef<Envelope>) {
  const progressPercent = computed(() => {
    if (!envelope.value.target_balance || envelope.value.target_balance <= 0) {
      return null
    }
    const percent = (envelope.value.current_balance / envelope.value.target_balance) * 100
    return Math.min(Math.max(percent, 0), 100)
  })

  const progressColor = computed(() => {
    if (progressPercent.value === null) return 'primary'
    if (progressPercent.value >= 100) return 'success'
    if (progressPercent.value >= 50) return 'primary'
    if (progressPercent.value >= 25) return 'warning'
    return 'error'
  })

  const balanceColor = computed(() => {
    if (envelope.value.current_balance < 0) return 'error'
    if (envelope.value.target_balance && envelope.value.current_balance >= envelope.value.target_balance) {
      return 'success'
    }
    return ''
  })

  return { progressPercent, progressColor, balanceColor }
}
