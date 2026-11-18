<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useHealthStore } from '../../stores/health'
import { applications, authorizedApplications } from '../../data/apps'
import type { AppDefinition } from '../../types/erp'
import AppIcon from '../AppIcon.vue'
import ERPSearchBar from './ERPSearchBar.vue'

const props = withDefaults(defineProps<{ apps?: AppDefinition[]; loading?: boolean; error?: string }>(), { apps: () => applications, error: '' })
const emit = defineEmits<{ retry: [] }>()
const auth = useAuthStore()
const health = useHealthStore()
const search = ref('')
const searchBar = ref<InstanceType<typeof ERPSearchBar>>()
const permitted = computed(() => auth.user ? authorizedApplications(props.apps, auth.activeCompany?.role) : [])
const filtered = computed(() => permitted.value.filter(app => `${app.name} ${app.description}`.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())))
function enabled(app: AppDefinition) { return app.status !== 'coming-soon' && (!app.requiresCompany || Boolean(auth.activeCompanyId)) }
function shortcut(event: KeyboardEvent) {
  if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !(event.target as HTMLElement).closest('input, textarea, select, [contenteditable="true"]')) {
    event.preventDefault(); searchBar.value?.focus()
  }
}
onMounted(() => document.addEventListener('keydown', shortcut))
onUnmounted(() => document.removeEventListener('keydown', shortcut))
</script>
<template>
  <section class="launcher-page" aria-labelledby="launcher-title" :aria-busy="loading">
    <div class="launcher-heading">
      <div><p class="eyebrow">ODOO PROJECT WORKSPACE</p><h1 id="launcher-title">Your applications</h1><p>One place for your business, with your team.</p></div>
      <ERPSearchBar ref="searchBar" v-model="search" label="Search applications" placeholder="Search applications…" :disabled="loading" />
    </div>
    <div class="launcher-context"><AppIcon name="building" /><div><strong>{{ auth.activeCompany?.name || 'Set up your workspace' }}</strong><span>{{ auth.activeCompany ? `Working as ${auth.activeCompany.role}` : 'Create or choose a company to use business applications.' }}</span></div><RouterLink to="/companies" class="text-link">{{ auth.activeCompany ? 'Manage companies' : 'Choose a company' }}</RouterLink></div>
    <p class="launcher-results" role="status" aria-live="polite">{{ loading ? 'Loading applications…' : `${filtered.length} ${search.trim() ? 'matching' : 'available'} applications` }}<span v-if="!loading && !search.trim()" class="search-hint">Press <kbd>/</kbd> to search</span></p>
    <div v-if="error" class="notice error" role="alert">{{ error }} <button type="button" class="inline-button" @click="emit('retry')">Retry</button></div>
    <div v-else-if="loading" class="launcher-grid" aria-hidden="true"><div v-for="index in 8" :key="index" class="launcher-skeleton"></div></div>
    <ul v-else-if="filtered.length" class="launcher-grid">
      <li v-for="app in filtered" :key="app.path">
        <component :is="enabled(app) ? RouterLink : 'div'" :to="enabled(app) ? app.path : undefined" class="launcher-tile" :class="{ 'is-disabled': !enabled(app) }" :aria-disabled="!enabled(app) || undefined">
          <span class="launcher-icon" :style="{ '--app-color': app.color }"><AppIcon :name="app.icon" /></span>
          <span class="launcher-tile-copy"><strong>{{ app.name }}</strong><small>{{ app.description }}</small><span v-if="!enabled(app)" class="availability-label">{{ app.status === 'coming-soon' ? 'Coming soon' : 'Choose a company' }}</span></span>
          <AppIcon v-if="enabled(app)" name="arrow" class="tile-arrow" />
        </component>
      </li>
    </ul>
    <div v-else class="empty-state"><AppIcon name="search" /><h2>{{ search.trim() ? 'No applications found' : 'No applications available' }}</h2><p>{{ search.trim() ? 'Try an application name or a task, such as “orders”.' : 'Your company membership determines which applications you can access.' }}</p><button v-if="search.trim()" type="button" class="button-secondary" @click="search = ''; searchBar?.focus()">Clear search</button></div>
    <section class="health-panel" aria-label="Connection status">
      <span class="health-symbol" :class="health.status" aria-hidden="true"><AppIcon :name="health.status === 'disconnected' ? 'warning' : 'connection'" /></span>
      <div class="health-copy"><h2>{{ health.status === 'connected' ? 'API & database connected' : health.status === 'checking' ? 'Checking API connection…' : 'Connection needs attention' }}</h2><p>{{ health.error || 'Each application loads and validates its own business data.' }}</p><span v-if="health.lastChecked" class="last-checked">Last checked {{ health.lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span></div>
      <button type="button" class="button-secondary" :disabled="health.checking" @click="health.check()">{{ health.checking ? 'Checking…' : 'Check connection' }}</button>
    </section>
  </section>
</template>
