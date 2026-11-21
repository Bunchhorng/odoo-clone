import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(/** @type {import('../types/erp').User | null} */ (null))
  const companies = ref(/** @type {import('../types/erp').Company[]} */ ([]))
  const activeCompanyId = ref(/** @type {number | null} */ (null))
  const error = ref('')
  const busy = ref(false)
  const loading = ref(false)
  const activeCompany = computed(() => companies.value.find(item => item.id === activeCompanyId.value))
  const canManage = computed(() => ['owner', 'admin'].includes(activeCompany.value?.role))
  let initialization
  let initialized = false
  let signInRequest
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
  async function refresh() {
    loading.value = true
    try { apply(await api('auth/session/')) }
    catch (err) { error.value = err.message; throw err }
    finally { loading.value = false }
  }
  function initialize() {
    if (initialized) return Promise.resolve()
    initialization ??= refresh()
      .then(() => { initialized = true })
      .catch(err => { error.value = err.message })
      .finally(() => { initialization = undefined })
    return initialization
  }
  async function signIn(email, password) {
    // A double click or an Enter key repeat must join the in-flight sign-in,
    // never create a second credential-bearing POST.
    if (signInRequest) return signInRequest
    signInRequest = (async () => {
    // The public session endpoint sets the CSRF cookie, including after network recovery.
      await refresh()
      apply(await api('auth/login/', { method: 'POST', data: { email, password } }))
    })()
    try { return await signInRequest }
    finally { signInRequest = undefined }
  }
  async function signUp(email, password, passwordConfirmation) {
    await refresh()
    apply(await api('auth/register/', { method: 'POST', data: { email, password, password_confirmation: passwordConfirmation } }))
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
  return { user, companies, activeCompanyId, activeCompany, canManage, busy, loading, error,
    initialize, refresh, clear, signIn, signUp, signOut, selectCompany, createCompany, registerLeaveGuard }
})
