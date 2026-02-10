import { ref, computed, type Ref } from 'vue'

/**
 * Composable for managing create/edit/delete dialog state.
 *
 * @example
 * ```typescript
 * const {
 *   showDialog,
 *   showDeleteDialog,
 *   editingItem,
 *   saving,
 *   deleting,
 *   isEditing,
 *   openCreate,
 *   openEdit,
 *   openDelete,
 *   closeDialog,
 *   closeDeleteDialog,
 * } = useFormDialog<Payee>()
 *
 * // Open create dialog
 * openCreate()
 *
 * // Open edit dialog for an item
 * openEdit(payee)
 *
 * // Open delete confirmation
 * openDelete(payee)
 * ```
 */
export function useFormDialog<T>() {
  const showDialog = ref(false)
  const showDeleteDialog = ref(false)
  const editingItem: Ref<T | null> = ref(null)
  const saving = ref(false)
  const deleting = ref(false)

  const isEditing = computed(() => editingItem.value !== null)

  function openCreate() {
    editingItem.value = null
    showDialog.value = true
  }

  function openEdit(item: T) {
    editingItem.value = item
    showDialog.value = true
  }

  function openDelete(item: T) {
    editingItem.value = item
    showDeleteDialog.value = true
  }

  function closeDialog() {
    showDialog.value = false
  }

  function closeDeleteDialog() {
    showDeleteDialog.value = false
  }

  function reset() {
    editingItem.value = null
    saving.value = false
    deleting.value = false
  }

  return {
    showDialog,
    showDeleteDialog,
    editingItem,
    saving,
    deleting,
    isEditing,
    openCreate,
    openEdit,
    openDelete,
    closeDialog,
    closeDeleteDialog,
    reset,
  }
}
