import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getHealth } from '../services/api'

export const useHealthStore = defineStore('health', () => {
  const status = ref('checking')
  const checking = ref(false)
  const lastChecked = ref(/** @type {Date | null} */ (null))
  const error = ref('')

  async function check() {
    if (checking.value) return
    checking.value = true
    try {
      await getHealth()
      status.value = 'connected'
      error.value = ''
    } catch (failure) {
      status.value = 'disconnected'
      error.value = failure.name === 'AbortError'
        ? 'The connection timed out. Check that your services are running.'
        : 'Could not reach the API and database. Check your Docker services and try again.'
    } finally {
      lastChecked.value = new Date()
      checking.value = false
    }
  }

  return { status, checking, lastChecked, error, check }
})
