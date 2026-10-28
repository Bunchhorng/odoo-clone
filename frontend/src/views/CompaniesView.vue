<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
const name = ref('')
const busy = ref(false)
const error = ref('')
const success = ref('')
async function create() {
  busy.value = true; error.value = ''; success.value = ''
  try { await auth.createCompany(name.value); name.value = ''; success.value = 'Company created. You are its owner, and it is now selected.' }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
async function select(id) {
  error.value = ''; success.value = ''
  try { await auth.selectCompany(id); success.value = `Now working in ${auth.activeCompany.name}.` }
  catch (err) { error.value = err.message }
}
</script>

<template>
  <section class="page-section">
    <p class="eyebrow">A SPACE FOR EACH BUSINESS</p><h1>Your companies.</h1><p class="intro">Your access stays separate in every company.</p>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p><p v-if="success" class="notice success" role="status">{{ success }}</p>
    <div class="content-columns">
      <section aria-labelledby="company-list-title"><h2 id="company-list-title">Available companies <span class="count">{{ auth.companies.length }}</span></h2><p v-if="!auth.companies.length" class="empty-state">You don’t belong to a company yet. Create one here, or ask an owner to add your email to their team.</p><div v-for="company in auth.companies" :key="company.id" class="panel company-card"><div><h3>{{ company.name }}</h3><span class="role-badge">{{ company.role }}</span></div><span v-if="company.id === auth.activeCompanyId" class="selected-label">✓ Current company</span><button v-else class="button-secondary" :disabled="auth.busy || busy" @click="select(company.id)">Switch company</button></div></section>
      <form class="panel" @submit.prevent="create"><h2>Create a company</h2><p class="muted">You will become the owner of the new workspace.</p><label>Company name<input v-model="name" name="company-name" maxlength="200" required :disabled="busy || auth.busy" /></label><button class="button-primary" :disabled="busy || auth.busy || !name.trim()">{{ busy ? 'Creating…' : 'Create company' }}</button><p class="form-help">Each company has its own team. Creating a company does not give other users access to it.</p></form>
    </div>
  </section>
</template>
