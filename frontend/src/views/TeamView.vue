<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
const members = ref([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const email = ref('')
const role = ref('member')
let generation = 0
const roles = computed(() => auth.activeCompany?.role === 'owner' ? ['member', 'admin', 'owner'] : ['member'])
const activeCount = computed(() => members.value.filter(item => item.is_active && item.user_is_active).length)
function editable(member) { return auth.activeCompany?.role === 'owner' || (auth.activeCompany?.role === 'admin' && member.role === 'member') }
function changed(member) { return member.draftRole !== member.role || member.draftActive !== member.is_active }
async function load() {
  // A company switch can overtake a request. Only the newest load may update the screen.
  const current = ++generation
  const companyId = auth.activeCompanyId
  members.value = []; error.value = ''; success.value = ''
  if (!companyId) { loading.value = false; return }
  loading.value = true
  try {
    const data = await api(`companies/${companyId}/members/`)
    if (current === generation) {
      members.value = data.members.map(item => ({ ...item, draftRole: item.role, draftActive: item.is_active }))
      return true
    }
  } catch (err) {
    if (current === generation) { error.value = err.message; if (err.status === 404) await auth.refresh().catch(() => {}) }
  } finally { if (current === generation) loading.value = false }
}
watch(() => auth.activeCompanyId, () => { email.value = ''; role.value = 'member'; load() }, { immediate: true })
async function mutate(action, message) {
  const companyId = auth.activeCompanyId
  // Keep the shared company selector disabled until this company-specific write finishes.
  busy.value = true; auth.busy = true; error.value = ''; success.value = ''
  try {
    await action(companyId)
    await auth.refresh()
    if (companyId === auth.activeCompanyId && await load()) success.value = message
  } catch (err) { if (companyId === auth.activeCompanyId) error.value = err.message }
  finally { busy.value = false; auth.busy = false }
}
async function add() {
  await mutate(id => api(`companies/${id}/members/`, { method: 'POST', data: { email: email.value, role: role.value } }), 'Teammate added. They can now sign in and select this company.')
  if (!error.value) { email.value = ''; role.value = 'member' }
}
async function save(member) {
  await mutate(id => api(`companies/${id}/members/${member.id}/`, { method: 'PATCH', data: { role: member.draftRole, is_active: member.draftActive } }), 'Team access updated.')
}
</script>

<template>
  <section class="page-section">
    <p class="eyebrow">GOOD WORK STARTS WITH PEOPLE</p><h1>Your team.</h1><p class="intro">{{ auth.activeCompany ? `Manage access to ${auth.activeCompany.name}.` : 'Choose or create a company to see its team.' }}</p>
    <p v-if="error" class="notice error" role="alert">{{ error }} <button v-if="!busy" class="inline-button" @click="load">Refresh team</button></p><p v-if="success" class="notice success" role="status">{{ success }}</p>
    <div v-if="!auth.activeCompany" class="empty-state"><RouterLink to="/companies" class="text-link">Open your companies →</RouterLink></div>
    <template v-else>
      <div class="section-heading team-heading"><h2>Company members</h2><span v-if="!loading">{{ activeCount }} active / {{ members.length }} total</span></div>
      <p v-if="loading" class="empty-state" role="status">Loading team…</p>
      <div v-else-if="members.length" class="team-list" :aria-busy="busy || auth.busy">
        <form v-for="member in members" :key="member.id" class="panel member-row" @submit.prevent="save(member)">
          <div class="member-identity"><span class="avatar" aria-hidden="true">{{ member.email[0].toUpperCase() }}</span><div><strong>{{ member.name }}</strong><span class="muted">{{ member.name !== member.email ? member.email : member.user_id === auth.user.id ? 'You' : 'Teammate' }}</span><span v-if="!member.user_is_active" class="warning-label">Account disabled by administrator</span></div></div>
          <template v-if="editable(member)"><label class="compact-label">Role<select v-model="member.draftRole" :aria-label="`Role for ${member.email}`" :disabled="busy || auth.busy"><option v-for="value in roles" :key="value" :value="value">{{ value }}</option></select></label><label class="checkbox-label"><input v-model="member.draftActive" type="checkbox" :aria-label="`Active access for ${member.email}`" :disabled="busy || auth.busy" /> Active access</label><button class="button-secondary" :disabled="busy || auth.busy || !changed(member)">Save</button></template>
          <template v-else><span class="role-badge">{{ member.role }}</span><span class="muted">{{ member.is_active ? 'Active access' : 'Access disabled' }}</span></template>
        </form>
      </div>
      <div class="content-columns team-details">
        <form v-if="auth.canManage" class="panel" @submit.prevent="add"><h2>Add a teammate</h2><p class="muted">Use an existing account’s email. Your Django administrator can create accounts first.</p><label>Email address<input v-model="email" name="teammate-email" type="email" required maxlength="254" :disabled="busy || auth.busy || loading" /></label><label>Role<select v-model="role" name="teammate-role" :disabled="busy || auth.busy || loading"><option v-for="value in roles" :key="value" :value="value">{{ value }}</option></select></label><button class="button-primary" :disabled="busy || auth.busy || loading">{{ busy ? 'Saving…' : 'Add teammate' }}</button><p class="form-help">Access is available immediately. No invitation email is sent. Disabled memberships can be reactivated in the list above.</p></form>
        <aside class="panel role-guide"><h2>How access works</h2><p><strong>Owner</strong> — manages all teammates and roles. At least one active owner must remain.</p><p><strong>Administrator</strong> — adds, disables, and reactivates members. An owner manages administrator and owner access.</p><p><strong>Member</strong> — views the team. Access changes require an owner or administrator.</p><p class="form-help">Disabling company access leaves the account and access to other companies in place.</p></aside>
      </div>
    </template>
  </section>
</template>
