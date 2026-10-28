<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { backendOrigin } from '../services/api'
import { erp, useWorkspace } from '../composables/erp'
const auth = useAuthStore()
const currency = ref('USD')
const success = ref('')
const { data, error, loading, refresh } = useWorkspace(id => erp(id, 'settings/'))
watch(data, value => { if (value) currency.value = value.currency; success.value = '' })
async function save() {
  auth.busy = true; error.value = ''; success.value = ''
  try { await erp(auth.activeCompanyId, 'settings/', { method: 'PATCH', data: { currency: currency.value } }); await refresh(); success.value = 'Company preferences saved.' }
  catch (err) { error.value = err.message }
  finally { auth.busy = false }
}
</script>
<template><section class="business-page"><div class="module-tabs"><RouterLink to="/settings" class="active">Preferences</RouterLink><RouterLink to="/companies">Companies</RouterLink><RouterLink to="/team">Users & access</RouterLink><RouterLink to="/setup">Getting started</RouterLink></div><div class="control-panel"><div class="control-title"><h1>Settings</h1><span class="muted">{{ auth.activeCompany?.name || 'Workspace preferences' }}</span></div></div><div class="workspace-content settings-content"><p v-if="error" class="notice error" role="alert">{{ error }}</p><p v-if="success" class="notice success" role="status">{{ success }}</p><p v-if="loading" role="status">Loading preferences…</p><div class="content-columns"><form v-if="data" class="panel" @submit.prevent="save"><h2>Company currency</h2><p class="muted">Set your business currency before creating your first quotation or purchase order.</p><label>Currency<select v-model="currency" name="currency" :disabled="!auth.canManage || data.currency_locked || auth.busy"><option v-for="value in ['USD', 'THB', 'EUR', 'GBP', 'SGD', 'AUD', 'CAD']" :key="value" :value="value">{{ value }}</option></select></label><p v-if="data.currency_locked" class="form-help">Currency is locked because this company already has orders. Each document retains its original currency.</p><button v-if="auth.canManage && !data.currency_locked" class="button-primary" :disabled="auth.busy">Save preferences</button></form><section class="panel"><h2>Your workspace</h2><p class="muted">Manage the companies and people behind your business.</p><div class="settings-links"><RouterLink to="/companies">Companies <span>Manage workspaces →</span></RouterLink><RouterLink to="/team">Team <span>Manage access →</span></RouterLink><RouterLink to="/setup">Getting started <span>Read the guide →</span></RouterLink><a v-if="auth.user?.is_staff" :href="`${backendOrigin}/admin/`">Django administration <span>Accounts and maintenance ↗</span></a></div></section></div><p v-if="!auth.activeCompanyId" class="notice">Create a company before setting business preferences. <RouterLink to="/companies" class="text-link">Open companies →</RouterLink></p></div></section></template>
