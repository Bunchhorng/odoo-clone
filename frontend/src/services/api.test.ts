import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, getHealth, waitForHealthy } from './api'

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules(); document.cookie = 'csrftoken=; max-age=0' })
describe('Django API integration', () => {
  it('uses the same-origin session and CSRF cookie for writes', async () => {
    document.cookie = 'csrftoken=security-token'
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ saved: true }), { status: 200 }))
    vi.stubGlobal('fetch', request)
    await api('companies/1/select/', { method: 'POST' })
    expect(request).toHaveBeenCalledWith('/api/v1/companies/1/select/', expect.objectContaining({ credentials: 'same-origin', cache: 'no-store', method: 'POST', headers: expect.objectContaining({ 'X-CSRFToken': 'security-token' }) }))
  })
  it('signals session expiry without replaying an unsafe request', async () => {
    const expired = vi.fn()
    window.addEventListener('session-expired', expired)
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'Please sign in.' }), { status: 401 }))
    vi.stubGlobal('fetch', request)
    try {
      await expect(api('companies/1/erp/contacts/', { method: 'POST', data: { name: 'Customer' } })).rejects.toMatchObject({ status: 401 })
      expect(expired).toHaveBeenCalledOnce()
      expect(request).toHaveBeenCalledOnce()
    } finally { window.removeEventListener('session-expired', expired) }
  })
  it('preserves CSRF and permission errors without signing the user out', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'Your security token expired.' }), { status: 403 })))
    await expect(api('companies/1/select/', { method: 'POST' })).rejects.toMatchObject({ status: 403, message: 'Your security token expired.' })
  })
  it('does not treat a successful HTML error page as business data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html><title>Just a moment...</title>Checking your browser</html>', { status: 200 })))
    await expect(api('auth/session/')).rejects.toThrow('HTML security challenge')
  })
  it('uses the same-origin API proxy even when a backend origin is configured', async () => {
    vi.stubEnv('VITE_BACKEND_ORIGIN', 'https://api.example.com/')
    vi.resetModules()
    const { api: deployedApi } = await import('./api')
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user: null }), { status: 200 }))
    vi.stubGlobal('fetch', request)

    await deployedApi('auth/session/')

    expect(request).toHaveBeenCalledWith('/api/v1/auth/session/',
      expect.objectContaining({ credentials: 'same-origin' }))
  })
})

describe('backend cold-start recovery', () => {
  function response(status: number, body: unknown, headers?: HeadersInit) {
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })
  }

  function clock() {
    let elapsed = 0
    return {
      now: () => elapsed,
      sleep: async (milliseconds: number) => { elapsed += milliseconds },
    }
  }

  it('retries HTTP 503 cold starts with exponential backoff until the API is healthy', async () => {
    const time = clock()
    const sleep = vi.fn(time.sleep)
    const request = vi.fn()
      .mockResolvedValueOnce(new Response('<html>Application is starting</html>', { status: 503, headers: { 'Content-Type': 'text/html' } }))
      .mockResolvedValueOnce(response(503, { error: 'Starting' }))
      .mockResolvedValueOnce(response(200, { status: 'ok', database: 'connected' }))
    vi.stubGlobal('fetch', request)

    await expect(waitForHealthy({ now: time.now, sleep })).resolves.toEqual({ status: 'ok', database: 'connected' })
    expect(request).toHaveBeenCalledTimes(3)
    expect(sleep).toHaveBeenNthCalledWith(1, 1_000)
    expect(sleep).toHaveBeenNthCalledWith(2, 2_000)
  })

  it('respects Retry-After for HTTP 429 instead of using its normal backoff', async () => {
    const time = clock()
    const sleep = vi.fn(time.sleep)
    const request = vi.fn()
      .mockResolvedValueOnce(response(429, { error: 'Try later' }, { 'Retry-After': '7' }))
      .mockResolvedValueOnce(response(200, { status: 'ok', database: 'connected' }))
    vi.stubGlobal('fetch', request)

    await waitForHealthy({ now: time.now, sleep })
    expect(sleep).toHaveBeenCalledWith(7_000)
    expect(request).toHaveBeenCalledTimes(2)
  })

  it('does not keep probing when Retry-After reaches the overall timeout', async () => {
    const request = vi.fn().mockResolvedValue(response(429, { error: 'Try later' }, { 'Retry-After': '120' }))
    vi.stubGlobal('fetch', request)

    await expect(waitForHealthy({ now: () => 0, sleep: vi.fn() })).rejects.toMatchObject({ status: 429 })
    expect(request).toHaveBeenCalledOnce()
  })

  it('recovers from a network failure using only the health endpoint', async () => {
    const time = clock()
    const request = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(response(200, { status: 'ok', database: 'connected' }))
    vi.stubGlobal('fetch', request)

    await expect(waitForHealthy({ now: time.now, sleep: time.sleep })).resolves.toMatchObject({ status: 'ok' })
    expect(request).toHaveBeenCalledTimes(2)
    expect(request.mock.calls.every(([url]) => url === '/api/v1/health/')).toBe(true)
  })

  it('accepts a valid health response and rejects HTML challenge pages', async () => {
    const request = vi.fn().mockResolvedValueOnce(response(200, { status: 'ok', database: 'connected' }))
    vi.stubGlobal('fetch', request)
    await expect(getHealth()).resolves.toMatchObject({ status: 'ok', database: 'connected' })

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<!doctype html><title>Just a moment...</title>', { status: 403, headers: { 'Content-Type': 'text/html' } })))
    await expect(getHealth()).rejects.toMatchObject({ securityChallenge: true, status: 403 })
  })
})
