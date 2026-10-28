import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const companies = ref([])
  const activeCompanyId = ref(null)
  const error = ref('')
  const busy = ref(false)
  const activeCompany = computed(() => companies.value.find(item => item.id === activeCompanyId.value))
  const canManage = computed(() => ['owner', 'admin'].includes(activeCompany.value?.role))
  let initialization
  const leaveGuards = new Set()
  function registerLeaveGuard(guard) {
    leaveGuards.add(guard)
    return () => leaveGuards.delete(guard)
  }
  function mayLeave() { return [...leaveGuards].every(guard => guard()) }
  function apply(data) {
    user.value = data.user
    companies.value = data.companies
    activeCompanyId.value = data.active_company_id
    error.value = ''
  }
  function clear() { apply({ user: null, companies: [], active_company_id: null }) }
  async function refresh() { apply(await api('auth/session/')) }
  function initialize() {
    initialization ??= refresh().catch(err => { error.value = err.message })
    return initialization
  }
  async function signIn(email, password) {
    // The public session endpoint sets the CSRF cookie, including after network recovery.
    await refresh()
    apply(await api('auth/login/', { method: 'POST', data: { email, password } }))
  }
  async function signOut() {
    if (!mayLeave()) return false
    await api('auth/logout/', { method: 'POST' })
    clear()
    return true
  }
  async function selectCompany(id) {
    if (id !== activeCompanyId.value && !mayLeave()) return false
    busy.value = true
    try { apply(await api(`companies/${id}/select/`, { method: 'POST' })); return true }
    finally { busy.value = false }
  }
  async function createCompany(name) {
    busy.value = true
    try { apply(await api('companies/', { method: 'POST', data: { name } })) }
    finally { busy.value = false }
  }
  return { user, companies, activeCompanyId, activeCompany, canManage, busy, error,
    initialize, refresh, clear, signIn, signOut, selectCompany, createCompany, registerLeaveGuard }
})
