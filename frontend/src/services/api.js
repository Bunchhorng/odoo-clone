const configuredBackendOrigin =
  import.meta.env.VITE_BACKEND_ORIGIN?.replace(/\/+$/, '') || ''

export const backendOrigin =
  configuredBackendOrigin || 'http://localhost:8000'

const apiOrigin = configuredBackendOrigin

const credentials = apiOrigin ? 'include' : 'same-origin'

function apiUrl(path) {
  const normalizedPath = path.replace(/^\/+/, '')
  return `${apiOrigin}/api/v1/${normalizedPath}`
}

/**
 * @param {string} path
 * @param {{ method?: string, data?: unknown, format?: string }} [options]
 */
export async function api(path, { method = 'GET', data, format = 'json' } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15000)
  const token = document.cookie.split('; ').find(item => item.startsWith('csrftoken='))?.slice(10)
  try {
    const response = await fetch(apiUrl(path), {
      method, credentials, cache: 'no-store', signal: controller.signal,
      headers: {
        Accept: format === 'text' ? 'text/csv' : 'application/json',
        ...(data !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(method !== 'GET' && token ? { 'X-CSRFToken': decodeURIComponent(token) } : {}),
      },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
    })
    if (response.ok && format === 'text') return response.text()
    if (response.ok && response.status === 204) return null
    const result = await response.json().catch(() => {
      if (response.ok) throw new Error('The server returned an unreadable response. Please try again.')
      return {}
    })
    if (!response.ok) {
      if (response.status === 401 && path !== 'auth/login/') window.dispatchEvent(new Event('session-expired'))
      const error = new Error(result.error || `The request failed (HTTP ${response.status}). Please try again.`)
      error.status = response.status
      error.retryAfter = Number(response.headers.get('Retry-After')) || null
      if (response.status === 429 && error.retryAfter) error.message += ` Try again in ${error.retryAfter} seconds.`
      throw error
    }
    return result
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Check your connection and try again.')
    if (error instanceof TypeError) throw new Error('Cannot reach the server. Check your connection and try again.')
    throw error
  } finally { clearTimeout(timer) }
}

export async function getHealth() {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(apiUrl('health/'), {
      credentials,
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!response.ok) throw new Error(`Service returned HTTP ${response.status}.`)
    const data = await response.json()
    if (data.status !== 'ok' || data.database !== 'connected') {
      throw new Error('The database connection is unavailable.')
    }
    return data
  } finally {
    clearTimeout(timeout)
  }
}
