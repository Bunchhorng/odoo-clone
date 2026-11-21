<script setup>
defineProps({
  unavailable: { type: Boolean, default: false },
  error: { type: String, default: '' },
  attempts: { type: Number, default: 0 },
})
defineEmits(['retry'])
</script>

<template>
  <main class="backend-starting-screen" aria-labelledby="backend-status-title">
    <section class="backend-starting-card" :aria-busy="!unavailable">
      <div class="backend-starting-brand" aria-hidden="true">o</div>
      <div v-if="!unavailable" class="backend-starting-spinner" aria-hidden="true"></div>
      <div v-else class="backend-starting-alert" aria-hidden="true">!</div>
      <p class="backend-starting-kicker">ODOO</p>
      <h1 id="backend-status-title">{{ unavailable ? 'Odoo server is unavailable.' : 'Starting odoo server. Please wait...' }}</h1>
      <p v-if="!unavailable" class="backend-starting-copy" role="status" aria-live="polite">Connecting securely to your workspace{{ attempts > 1 ? ` (attempt ${attempts})` : '' }}.</p>
      <template v-else>
        <p class="backend-starting-copy" role="alert">{{ error || 'We could not connect to the server within two minutes.' }}</p>
        <button type="button" class="backend-retry-button" @click="$emit('retry')">Retry</button>
      </template>
    </section>
  </main>
</template>
