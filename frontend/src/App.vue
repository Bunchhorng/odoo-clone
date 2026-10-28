<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { modules } from './data/modules'
import AppIcon from './components/AppIcon.vue'
import { useHealthStore } from './stores/health'
import { useAuthStore } from './stores/auth'

const health = useHealthStore()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const currentApp = computed(() => modules.find(item => route.path.startsWith(item.path))?.name || (route.path === '/tasks' ? 'Project' : route.path === '/companies' ? 'Settings' : 'Applications'))
const error = ref('')
const signingOut = ref(false)
const statusLabel = computed(() => ({ checking: 'Checking connection', connected: 'API connected', disconnected: 'API disconnected' })[health.status])
let interval
onMounted(() => { health.check(); interval = setInterval(() => health.check(), 30000) })
onUnmounted(() => clearInterval(interval))
async function switchCompany(event) {
  error.value = ''
  try { await auth.selectCompany(Number(event.target.value)) }
  catch (err) { error.value = err.message }
  event.target.value = auth.activeCompanyId ?? ''
}
async function signOut() {
  signingOut.value = true; error.value = ''
  try { if (await auth.signOut()) await router.push('/login') }
  catch (err) { error.value = err.message }
  finally { signingOut.value = false }
}
</script>

<template>
  <div class="workspace-shell" :class="{ launcher: route.path === '/' && auth.user }">
    <a href="#main-content" class="skip-link">Skip to content</a>
    <header class="site-header">
      <RouterLink to="/" class="brand" aria-label="KERP home"><span class="brand-mark" aria-hidden="true">k</span><span>KERP<span class="brand-subtitle">Workspace</span></span></RouterLink>
      <details v-if="auth.user" class="app-dropdown"><summary aria-label="Open applications"><AppIcon name="grid" /><span>{{ currentApp }}</span></summary><div class="app-menu" @click="$event.target.closest('details')?.removeAttribute('open')"><RouterLink v-for="app in modules" :key="app.path" :to="app.path"><AppIcon :name="app.icon" /><span>{{ app.name }}</span></RouterLink></div></details>
      <nav aria-label="Main navigation">
        <template v-if="auth.user"><RouterLink to="/" exact-active-class="active">Apps</RouterLink><RouterLink to="/companies" active-class="active">Companies</RouterLink><RouterLink to="/team" active-class="active">Team</RouterLink></template>
        <RouterLink to="/setup" active-class="active">Guide</RouterLink><RouterLink v-if="!auth.user" to="/login" active-class="active">Sign in</RouterLink>
      </nav>
      <span class="connection-badge" :class="health.status" role="status"><span class="status-dot" aria-hidden="true"></span>{{ statusLabel }}</span>
    </header>
    <div v-if="auth.user" class="account-bar">
      <label v-if="auth.companies.length" class="company-picker">Working in<select aria-label="Active company" :value="auth.activeCompanyId" :disabled="auth.busy || signingOut" @change="switchCompany"><option v-for="company in auth.companies" :key="company.id" :value="company.id">{{ company.name }}</option></select><span class="role-badge">{{ auth.activeCompany?.role }}</span></label>
      <RouterLink v-else to="/companies" class="text-link">Create your first company</RouterLink>
      <div class="account-actions"><RouterLink to="/account" class="account-link" aria-label="Account and security">{{ auth.user.email }}</RouterLink><button class="button-secondary" :disabled="signingOut || auth.busy" @click="signOut">{{ signingOut ? 'Signing out…' : 'Sign out' }}</button></div>
    </div>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>
    <main id="main-content" tabindex="-1"><RouterView /></main>
    <footer class="site-footer"><span>KERP / Your business, connected</span><span class="local-label"><span class="status-dot" aria-hidden="true"></span>Local development</span></footer>
  </div>
</template>
