export const backendOrigin = import.meta.env.VITE_BACKEND_ORIGIN || 'http://localhost:8000'

export async function getHealth() {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch('/api/v1/health/', {
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
