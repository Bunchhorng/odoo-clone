import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { waitForHealthy } from '../services/api'

export const useHealthStore = defineStore('health', () => {
  const status = ref('checking')
  const checking = ref(false)
  const lastChecked = ref(/** @type {Date | null} */ (null))
  const error = ref('')
  const attempts = ref(0)
  const isAvailable = computed(() => status.value === 'connected')
  let checkPromise

  async function check() {
    if (isAvailable.value) return true
    if (checkPromise) return checkPromise
    checking.value = true
    status.value = 'checking'
    error.value = ''
    attempts.value = 0
    checkPromise = waitForHealthy({ onAttempt: attempt => { attempts.value = attempt } })
      .then(() => {
        status.value = 'connected'
        error.value = ''
        return true
      })
      .catch(failure => {
        status.value = 'unavailable'
        error.value = failure.message || 'The server is still unavailable.'
        return false
      })
      .finally(() => {
        lastChecked.value = new Date()
        checking.value = false
        checkPromise = undefined
      })
    return checkPromise
  }

  // This only starts a new health-only recovery cycle after a previous one has
  // ended. It never retries a login or any other unsafe request.
  function retry() {
    return check()
  }

  return { status, checking, lastChecked, error, attempts, isAvailable, check, retry }
})
