<script setup>
import { onMounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import ERPAppShell from './components/erp/ERPAppShell.vue'
import BackendStartingScreen from './components/BackendStartingScreen.vue'
import { useAuthStore } from './stores/auth'
import { useHealthStore } from './stores/health'

const router = useRouter()
const auth = useAuthStore()
const health = useHealthStore()

onMounted(() => { health.check() })

async function retryBackend() {
  if (!await health.retry()) return
  await auth.initialize()
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth && !auth.user) {
    await router.replace({ name: 'login', query: { next: currentRoute.fullPath } })
  } else if (['login', 'register'].includes(String(currentRoute.name)) && auth.user) {
    await router.replace({ name: 'home' })
  }
}
</script>
<template>
  <BackendStartingScreen
    v-if="!health.isAvailable"
    :unavailable="health.status === 'unavailable'"
    :error="health.error"
    :attempts="health.attempts"
    @retry="retryBackend"
  />
  <ERPAppShell v-else><RouterView /></ERPAppShell>
</template>
