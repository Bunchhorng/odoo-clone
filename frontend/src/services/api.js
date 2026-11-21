// API requests deliberately stay relative to the frontend origin. In production
// the worker proxies /api to Render; locally Vite does the same. This keeps
// Django session and CSRF cookies first-party. backendOrigin remains only for
// the existing direct Django Admin links.
const configuredBackendOrigin = import.meta.env.VITE_BACKEND_ORIGIN?.replace(/\/+$/, '') || ''
export const backendOrigin = configuredBackendOrigin || 'http://localhost:8000'
const apiOrigin = ''
const credentials = 'same-origin'

export const HEALTH_RETRY_TIMEOUT_MS = 120_000
const HEALTH_REQUEST_TIMEOUT_MS = 10_000
const HEALTH_INITIAL_BACKOFF_MS = 1_000
const HEALTH_MAX_BACKOFF_MS = 15_000

function apiUrl(path) {
  const normalizedPath = path.replace(/^\/+/, '')
  return `${apiOrigin}/api/v1/${normalizedPath}`
}

function parseRetryAfter(value, now = Date.now()) {
  if (!value) return null
  if (/^\d+$/.test(value.trim())) return Number(value) * 1_000
  const retryAt = Date.parse(value)
  return Number.isNaN(retryAt) ? null : Math.max(0, retryAt - now)
}

function looksLikeHtml(response, body) {
  return response.headers.get('content-type')?.toLowerCase().includes('text/html') ||
    /^\s*(?:<!doctype html|<html\b)/i.test(body)
}

function isSecurityChallenge(body) {
  return /(?:just a moment|checking your browser|security check|captcha|attention required|cloudflare)/i.test(body)
}

function requestError(message, response, { securityChallenge = false } = {}) {
  const error = new Error(message)
  error.status = response.status
  error.retryAfter = parseRetryAfter(response.headers.get('Retry-After'))
  error.securityChallenge = securityChallenge
  return error
}

async function readJson(response) {
  const body = await response.text()
  if (looksLikeHtml(response, body)) {
    const securityChallenge = isSecurityChallenge(body)
    throw requestError(
      securityChallenge
        ? 'The server returned an HTML security challenge instead of an API response.'
        : 'The server returned HTML instead of an API response.',
      response,
      { securityChallenge },
    )
  }
  try {
    return body ? JSON.parse(body) : null
  } catch {
    throw requestError('The server returned an unreadable response. Please try again.', response)
  }
}

/**
 * @param {string} path
 * @param {{ method?: string, data?: unknown, format?: string }} [options]
 */
export async function api(path, { method = 'GET', data, format = 'json' } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15_000)
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
    const result = await readJson(response)
    if (!response.ok) {
      if (response.status === 401 && path !== 'auth/login/') window.dispatchEvent(new Event('session-expired'))
      const error = requestError(result?.error || `The request failed (HTTP ${response.status}). Please try again.`, response)
      if (response.status === 429 && error.retryAfter) error.message += ` Try again in ${Math.ceil(error.retryAfter / 1_000)} seconds.`
      throw error
    }
    return result
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Check your connection and try again.')
    if (error instanceof TypeError) throw new Error('Cannot reach the server. Check your connection and try again.')
    throw error
  } finally { clearTimeout(timer) }
}

/**
 * Make one health request. Retrying is intentionally implemented separately so
 * no POST or other business request can be replayed during a cold start.
 */
export async function getHealth({ timeoutMs = HEALTH_REQUEST_TIMEOUT_MS } = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(apiUrl('health/'), {
      credentials,
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    const data = await readJson(response)
    if (!response.ok) throw requestError(data?.error || `Service returned HTTP ${response.status}.`, response)
    if (data?.status !== 'ok' || data?.database !== 'connected') {
      throw requestError('The database connection is unavailable.', response)
    }
    return data
  } catch (error) {
    if (error.name === 'AbortError') {
      const timeoutError = new Error('The health check timed out.')
      timeoutError.transient = true
      throw timeoutError
    }
    if (error instanceof TypeError) {
      const networkError = new Error('Cannot reach the server.')
      networkError.transient = true
      throw networkError
    }
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

function canRetryHealth(error) {
  if (error.securityChallenge) return false
  if (error.transient) return true
  return error.status === 408 || error.status === 425 || error.status === 429 || error.status >= 500
}

function delay(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}

/**
 * Retry only GET /health/ while a Render instance wakes. Dependencies are
 * injectable to keep timing and HTTP behavior deterministic in tests.
 */
export async function waitForHealthy({
  timeoutMs = HEALTH_RETRY_TIMEOUT_MS,
  requestHealth = getHealth,
  sleep = delay,
  now = () => Date.now(),
  onAttempt,
} = {}) {
  const startedAt = now()
  let attempt = 0
  let failure

  while (now() - startedAt < timeoutMs) {
    const remaining = timeoutMs - (now() - startedAt)
    onAttempt?.(attempt + 1)
    try {
      return await requestHealth({ timeoutMs: Math.min(HEALTH_REQUEST_TIMEOUT_MS, remaining) })
    } catch (error) {
      failure = error
      const remainingAfterRequest = timeoutMs - (now() - startedAt)
      if (!canRetryHealth(error) || remainingAfterRequest <= 0) throw error

      const exponentialBackoff = Math.min(HEALTH_INITIAL_BACKOFF_MS * (2 ** attempt), HEALTH_MAX_BACKOFF_MS)
      // Retry-After is a lower bound. Keep exponential backoff for a zero or
      // unusually short value so a throttled proxy is not hammered.
      const retryDelay = Math.max(error.retryAfter ?? 0, exponentialBackoff)
      // A Retry-After beyond our user-facing deadline should not produce more
      // probes. The user can deliberately try again once that window passes.
      if (retryDelay >= remainingAfterRequest) throw error

      await sleep(retryDelay)
      attempt += 1
    }
  }
  throw failure || new Error('The server is still unavailable.')
}
