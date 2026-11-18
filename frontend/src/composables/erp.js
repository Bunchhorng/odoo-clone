import { ref, watch, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { api } from '../services/api'

export function useWorkspace(loader, dependencies = []) {
  const auth = useAuthStore()
  const data = ref(null)
  const error = ref('')
  const loading = ref(false)
  let generation = 0
  async function refresh() {
    const current = ++generation
    const companyId = auth.activeCompanyId
    data.value = null; error.value = ''
    if (!companyId) { loading.value = false; return }
    loading.value = true
    try {
      const result = await loader(companyId)
      if (current === generation) data.value = result
    } catch (err) {
      if (current === generation) {
        error.value = err.message
        if (err.status === 404) await auth.refresh().catch(() => {})
      }
    } finally { if (current === generation) loading.value = false }
  }
  watch([() => auth.activeCompanyId, ...dependencies], refresh, { immediate: true })
  onUnmounted(() => { generation++ })
  return { data, error, loading, refresh }
}

export function erp(companyId, endpoint, options) {
  return api(`companies/${companyId}/erp/${endpoint}`, options)
}

export async function allRecords(companyId, resource, filters = {}) {
  const records = []
  let page = 1
  while (true) {
    const params = new URLSearchParams({ ...filters, page_size: '100', page: String(page) })
    const result = await erp(companyId, `${resource}/?${params}`)
    records.push(...result.results)
    if (records.length >= result.count || !result.results.length) return records
    page++
  }
}

export function money(value, currency = 'USD') {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(value || 0))
}
export function dateLabel(value) { return value ? new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleDateString() : '—' }
export function today() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}
