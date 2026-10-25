<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useHealthStore } from './stores/health'

const health = useHealthStore()
const statusLabel = computed(() => ({
  checking: 'Checking connection',
  connected: 'API connected',
  disconnected: 'API disconnected',
})[health.status])
let interval

onMounted(() => {
  health.check()
  interval = setInterval(() => health.check(), 30000)
})
onUnmounted(() => clearInterval(interval))
</script>

<template>
  <div class="workspace-shell">
    <header class="site-header">
      <RouterLink to="/" class="brand" aria-label="KERP home">
        <span class="brand-mark" aria-hidden="true">k</span>
        <span>KERP<span class="brand-subtitle">Workspace</span></span>
      </RouterLink>
      <nav aria-label="Main navigation">
        <RouterLink to="/" exact-active-class="active">Overview</RouterLink>
        <RouterLink to="/setup" active-class="active">Getting started</RouterLink>
      </nav>
      <span class="connection-badge" :class="health.status" role="status">
        <span class="status-dot" aria-hidden="true"></span>{{ statusLabel }}
      </span>
    </header>
    <main id="main-content"><RouterView /></main>
    <footer class="site-footer">
      <span>KERP <span aria-hidden="true">/</span> A foundation for your business</span>
      <span class="local-label"><span class="status-dot" aria-hidden="true"></span>Local development</span>
    </footer>
  </div>
</template>
