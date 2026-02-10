import { ref } from 'vue'

const isOpen = ref(true)

export function useNavDrawer() {
  function toggleDrawer() {
    isOpen.value = !isOpen.value
  }

  function openDrawer() {
    isOpen.value = true
  }

  function closeDrawer() {
    isOpen.value = false
  }

  return {
    isOpen,
    toggleDrawer,
    openDrawer,
    closeDrawer,
  }
}
