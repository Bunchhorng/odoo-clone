<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { apps } from '../data/apps'
import { useHealthStore } from '../stores/health'

const health = useHealthStore()
const checkedAt = computed(() => health.lastChecked?.toLocaleTimeString([], {
  hour: '2-digit', minute: '2-digit', second: '2-digit',
}))
</script>

<template>
  <section class="welcome">
    <p class="eyebrow">YOUR WORKSPACE, CONNECTED</p>
    <h1>A good place<br />to build your business.</h1>
    <p class="intro">Welcome to KERP. Manage your team and companies,<br class="desktop-break" /> check your connections, and make this workspace your own.</p>
    <div class="welcome-note"><span class="note-line"></span>Start small. Build together.</div>
  </section>

  <section class="apps-section" aria-labelledby="apps-heading">
    <div class="section-heading"><h2 id="apps-heading">Your workspace</h2><span>03 essentials</span></div>
    <div class="app-grid">
      <component :is="app.route ? RouterLink : 'a'" v-for="app in apps" :key="app.title"
        :to="app.route" :href="app.href" class="app-card">
        <span class="app-icon" :class="app.tone" aria-hidden="true">{{ app.icon }}</span>
        <h3>{{ app.title }}</h3>
        <p>{{ app.description }}</p>
        <span class="card-action">{{ app.label }}<span aria-hidden="true">↗</span></span>
      </component>
    </div>
  </section>

  <section class="health-panel" aria-labelledby="health-heading">
    <div class="health-symbol" :class="health.status" aria-hidden="true">{{ health.status === 'connected' ? '✓' : '·' }}</div>
    <div class="health-copy" aria-live="polite">
      <h2 id="health-heading">{{ health.status === 'connected' ? 'Everything is connected.' : health.status === 'checking' ? 'Checking your connection…' : 'Your connection needs attention.' }}</h2>
      <p v-if="health.error">{{ health.error }}</p>
      <p v-else-if="health.status === 'connected'">Your API and database are ready. You’re all set to get started.</p>
      <p v-else>Checking the API and database.</p>
      <span v-if="checkedAt" class="last-checked">Last checked {{ checkedAt }} · refreshes every 30 seconds</span>
    </div>
    <button type="button" class="button-secondary" :disabled="health.checking" @click="health.check()">
      <span aria-hidden="true">↻</span> {{ health.checking ? 'Checking…' : 'Check again' }}
    </button>
  </section>
</template>
