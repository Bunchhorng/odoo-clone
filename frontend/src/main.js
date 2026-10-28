import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/erp.css'
import './assets/components.css'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
createApp(App).use(pinia).use(router).mount('#app')
window.addEventListener('session-expired', () => {
  useAuthStore(pinia).clear()
  router.replace({ name: 'login', query: { expired: '1', next: router.currentRoute.value.fullPath } })
})
