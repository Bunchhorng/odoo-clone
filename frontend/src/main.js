import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/tailwind.css'
import './assets/tokens.css'
import './assets/main.css'
import './assets/erp.css'
import './assets/components.css'
import './assets/workspace.css'
import { initializeTheme } from './composables/theme'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
initializeTheme()
const app = createApp(App).use(pinia).use(router)
router.isReady().then(() => app.mount('#app'))
window.addEventListener('session-expired', () => {
  useAuthStore(pinia).clear()
  router.replace({ name: 'login', query: { expired: '1', next: router.currentRoute.value.fullPath } })
})
