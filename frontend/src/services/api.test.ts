import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

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
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Unexpected proxy response</html>', { status: 200 })))
    await expect(api('auth/session/')).rejects.toThrow('unreadable response')
  })
  it('uses the configured API origin and sends cross-origin credentials in production', async () => {
    vi.stubEnv('VITE_BACKEND_ORIGIN', 'https://api.example.com/')
    vi.resetModules()
    const { api: deployedApi } = await import('./api')
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user: null }), { status: 200 }))
    vi.stubGlobal('fetch', request)

    await deployedApi('auth/session/')

    expect(request).toHaveBeenCalledWith('https://api.example.com/api/v1/auth/session/',
      expect.objectContaining({ credentials: 'include' }))
  })
})
