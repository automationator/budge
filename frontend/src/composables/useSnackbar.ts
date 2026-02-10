import { reactive, ref } from 'vue'

// Snackbar auto-dismiss timeout in milliseconds
export const SNACKBAR_TIMEOUT = 5000

// Global snackbar state
export const snackbar = reactive({
  show: false,
  message: '',
  color: 'info',
  progress: 100,
})

// Trigger that increments each time showSnackbar is called (to restart countdown)
export const snackbarTrigger = ref(0)

export function showSnackbar(message: string, color = 'info') {
  snackbar.message = message
  snackbar.color = color
  snackbar.show = true
  snackbarTrigger.value++
}
