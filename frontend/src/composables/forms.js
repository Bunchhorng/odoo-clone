import { computed, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export function useDirtyForm(form) {
  const auth = useAuthStore()
  const saved = ref(JSON.stringify(form.value))
  const dirty = computed(() => JSON.stringify(form.value) !== saved.value)
  function markClean() { saved.value = JSON.stringify(form.value) }
  function discard() { form.value = JSON.parse(saved.value) }
  function mayLeave() {
    if (!dirty.value) return true
    if (!window.confirm('Discard your unsaved changes?')) return false
    discard()
    return true
  }
  onBeforeRouteLeave(mayLeave)
  onBeforeRouteUpdate(mayLeave)
  function beforeUnload(event) {
    if (dirty.value) { event.preventDefault(); event.returnValue = '' }
  }
  window.addEventListener('beforeunload', beforeUnload)
  const unregister = auth.registerLeaveGuard(mayLeave)
  onUnmounted(() => { unregister(); window.removeEventListener('beforeunload', beforeUnload) })
  return { dirty, markClean, discard }
}

export function usePage(resetSources = []) {
  const auth = useAuthStore()
  const page = ref(1)
  // Run before data watchers so switching companies never requests the old page.
  watch([() => auth.activeCompanyId, ...resetSources], () => { page.value = 1 }, { flush: 'sync' })
  return page
}

export function syncPage(page, data) {
  watch(data, value => {
    if (value?.page && value.page !== page.value) page.value = value.page
  })
}
