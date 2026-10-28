<script setup>
import { computed, ref } from 'vue'
import { modules } from '../data/modules'
import AppIcon from '../components/AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import { useHealthStore } from '../stores/health'
const auth = useAuthStore()
const health = useHealthStore()
const search = ref('')
const filtered = computed(() => modules.filter(app => `${app.name} ${app.description}`.toLowerCase().includes(search.value.toLowerCase())))
</script>
<template>
  <section class="launcher-page">
    <div class="launcher-heading"><div><h1>Your apps</h1><p>{{ auth.activeCompany?.name || 'A workspace for your whole business' }}</p></div><label class="search-field"><AppIcon name="search" /><input v-model="search" aria-label="Search applications" placeholder="Search applications…" /></label></div>
    <p v-if="!auth.activeCompany" class="notice">Start by creating your company. <RouterLink to="/companies" class="text-link">Create a company →</RouterLink></p>
    <div class="launcher-grid"><RouterLink v-for="app in filtered" :key="app.path" :to="app.path" class="launcher-tile"><span class="launcher-icon" :style="{ '--app-color': app.color }"><AppIcon :name="app.icon" /></span><span>{{ app.name }}</span><small>{{ app.description }}</small></RouterLink></div>
    <p v-if="!filtered.length" class="notice">No applications match your search.</p>
    <section class="health-panel"><div class="health-copy" aria-live="polite"><h2>{{ health.status === 'connected' ? 'Your workspace is ready' : health.status === 'checking' ? 'Checking connection…' : 'Connection needs attention' }}</h2><p>{{ health.error || 'Your business data stays connected across applications.' }}</p></div><button class="button-secondary" :disabled="health.checking" @click="health.check()">{{ health.checking ? 'Checking…' : 'Check connection' }}</button></section>
  </section>
</template>
