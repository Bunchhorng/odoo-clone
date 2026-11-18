<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useHealthStore } from '../../stores/health'
import { activeApplication, appCatalogue, applications, authorizedApplications, moduleNavigation, pageLabel, type AppCatalogueEntry } from '../../data/apps'
import { useTheme, type ThemePreference } from '../../composables/theme'
import AppIcon from '../AppIcon.vue'
import ERPPopover from './ERPPopover.vue'
import ERPCompanySwitcher from './ERPCompanySwitcher.vue'
import ERPNotificationCenter from './ERPNotificationCenter.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const health = useHealthStore()
const { preference, setTheme } = useTheme()
const currentApp = computed(() => activeApplication(route.path))
const apps = computed(() => authorizedApplications(applications, auth.activeCompany?.role))
const navigation = computed(() => moduleNavigation[currentApp.value?.path || ''] || [])
const label = computed(() => pageLabel(route.path))
const recordLabel = computed(() => {
  const id = route.params.recordId
  return id ? (id === 'new' ? 'New record' : `Record ${id}`) : ''
})
const error = ref('')
const signingOut = ref(false)
const switchSearch = ref('')
const filteredCatalogue = computed(() => {
  const query = switchSearch.value.trim().toLocaleLowerCase()
  return appCatalogue.map(category => ({ ...category, entries: category.entries.filter(entry => !query || `${category.name} ${entry.name}`.toLocaleLowerCase().includes(query)) })).filter(category => category.entries.length)
})
const initials = computed(() => (auth.user?.name || auth.user?.email || 'K').slice(0, 1).toUpperCase())
const currentYear = new Date().getFullYear()
let interval: ReturnType<typeof setInterval>
function checkWhenVisible() { if (document.visibilityState === 'visible') health.check() }
onMounted(() => {
  health.check()
  interval = setInterval(checkWhenVisible, 30000)
  document.addEventListener('visibilitychange', checkWhenVisible)
})
onUnmounted(() => { clearInterval(interval); document.removeEventListener('visibilitychange', checkWhenVisible) })
watch(() => route.fullPath, () => {
  error.value = ''
  document.title = `${label.value} · Odoo`
  document.getElementById('main-content')?.focus({ preventScroll: true })
})
async function signOut() {
  signingOut.value = true; error.value = ''
  try { if (await auth.signOut()) await router.push('/login') }
  catch (failure) { error.value = (failure as Error).message }
  finally { signingOut.value = false }
}
function activeLink(path: string) {
  if (path === currentApp.value?.path && route.params.recordId) return true
  return route.path === path
}
function applicationFor(entry: AppCatalogueEntry) { return entry.path ? apps.value.find(app => app.path === entry.path) : undefined }
function entryEnabled(entry: AppCatalogueEntry) { const app = applicationFor(entry); return Boolean(app && app.status !== 'coming-soon' && (!app.requiresCompany || auth.activeCompanyId)) }
function entryStatus(entry: AppCatalogueEntry) { return applicationFor(entry) ? 'Choose a company' : 'Coming soon' }
</script>

<template>
  <div class="workspace-shell" :class="{ 'is-launcher': route.path === '/' && auth.user }">
    <a href="#main-content" class="skip-link">Skip to content</a>
    <header class="site-header">
      <RouterLink to="/" class="brand" aria-label="Odoo home"><span class="brand-mark" aria-hidden="true">o</span><span>Odoo</span></RouterLink>
      <ERPPopover v-if="auth.user" label="Open applications" panel-class="app-switcher-panel apps-mega-panel">
        <template #trigger><AppIcon name="grid" /><span class="current-app">{{ currentApp?.name || 'Applications' }}</span><AppIcon name="chevron" class="chevron" /></template>
        <template #default>
          <div class="app-switcher-heading"><strong>Applications</strong><RouterLink to="/" class="text-link">View all</RouterLink></div>
          <label class="switcher-search"><span class="sr-only">Find an application</span><input v-model="switchSearch" type="search" placeholder="Find an application…" /></label>
          <nav class="app-menu" aria-label="Applications">
            <section v-for="category in filteredCatalogue" :key="category.name" class="app-menu-category" :class="`tone-${category.tone}`"><h2>{{ category.name }}</h2><div class="app-menu-links"><template v-for="entry in category.entries" :key="entry.name"><RouterLink v-if="entryEnabled(entry)" :to="entry.path!" :aria-current="currentApp?.path === entry.path ? 'page' : undefined">{{ entry.name }}</RouterLink><span v-else class="disabled-app" aria-disabled="true">{{ entry.name }}<small>{{ entryStatus(entry) }}</small></span></template></div></section>
          </nav>
          <p v-if="!filteredCatalogue.length" role="status" class="muted">No matching applications.</p>
        </template>
      </ERPPopover>
      <nav v-else class="public-navigation" aria-label="Main navigation"><RouterLink to="/setup">Guide</RouterLink><RouterLink to="/login">Sign in</RouterLink><RouterLink to="/register">Register</RouterLink></nav>
      <nav v-if="auth.user && route.path === '/'" class="launcher-primary-nav" aria-label="Workspace navigation">
        <RouterLink to="/">Apps</RouterLink><RouterLink to="/dashboard">Overview</RouterLink><RouterLink to="/crm">CRM</RouterLink><RouterLink to="/sales">Sales</RouterLink><RouterLink to="/inventory">Inventory</RouterLink>
      </nav>
      <div class="shell-tools">
        <ERPNotificationCenter v-if="auth.user" />
        <ERPPopover :label="auth.user ? 'User account menu' : 'Appearance'" panel-class="account-popover">
          <template #trigger><span v-if="auth.user" class="user-avatar" aria-hidden="true">{{ initials }}</span><AppIcon v-else name="settings" /><AppIcon name="chevron" class="chevron" /></template>
          <template #default>
            <div v-if="auth.user" class="account-identity"><strong>{{ auth.user.name }}</strong><span>{{ auth.user.email }}</span></div>
            <nav v-if="auth.user" aria-label="User account" class="account-menu-links"><RouterLink to="/account">Account &amp; security</RouterLink><RouterLink to="/setup">Getting started</RouterLink></nav>
            <label class="theme-control">Appearance<select :value="preference" aria-label="Appearance" @change="setTheme(($event.target as HTMLSelectElement).value as ThemePreference)"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
            <button v-if="auth.user" type="button" class="button-secondary sign-out" :disabled="auth.busy || signingOut" @click="signOut">{{ signingOut ? 'Signing out…' : 'Sign out' }}</button>
          </template>
        </ERPPopover>
      </div>
    </header>
    <div v-if="auth.user" class="workspace-context">
      <nav class="shell-breadcrumbs" aria-label="Breadcrumb"><RouterLink to="/">Apps</RouterLink><template v-if="route.path !== '/'"><span aria-hidden="true">/</span><RouterLink v-if="recordLabel && currentApp" :to="currentApp.path">{{ label }}</RouterLink><span v-else aria-current="page">{{ label }}</span><template v-if="recordLabel"><span aria-hidden="true">/</span><span aria-current="page">{{ recordLabel }}</span></template></template></nav>
      <ERPCompanySwitcher :disabled="signingOut" />
    </div>
    <nav v-if="auth.user && navigation.length" class="module-tabs" :aria-label="`${currentApp?.name} navigation`">
      <RouterLink v-for="item in navigation" :key="item.path" :to="item.path" :class="{ active: activeLink(item.path) }" :aria-current="activeLink(item.path) ? 'page' : undefined">{{ item.label }}</RouterLink>
    </nav>
    <div v-if="error" class="shell-feedback"><p class="notice error" role="alert">{{ error }}</p></div>
    <main id="main-content" tabindex="-1"><slot /></main>
    <footer class="site-footer">
      <div class="footer-brand"><span class="footer-mark" aria-hidden="true">o</span><div><strong>Odoo</strong><span>One workspace for every team.</span></div></div>
      <nav class="footer-links" aria-label="Footer navigation"><RouterLink v-if="auth.user" to="/">Applications</RouterLink><RouterLink to="/setup">Workspace guide</RouterLink><RouterLink v-if="auth.user" to="/account">Account</RouterLink><RouterLink v-else to="/login">Sign in</RouterLink></nav>
      <div class="footer-meta"><span>© {{ currentYear }} Odoo</span><span v-if="auth.activeCompany">{{ auth.activeCompany.name }}</span></div>
    </footer>
  </div>
</template>
