import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../services/api', () => ({ api: vi.fn() }))

import { api } from '../services/api'
import { useAuthStore } from './auth'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('sign-in submission', () => {
  it('joins duplicate submissions and posts login credentials only once', async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({ user: null, companies: [], active_company_id: null })
      .mockResolvedValueOnce({ user: { id: 1, name: 'Ada', email: 'ada@example.test', is_staff: false }, companies: [], active_company_id: null })
    const auth = useAuthStore()

    await Promise.all([
      auth.signIn('ada@example.test', 'correct horse battery staple'),
      auth.signIn('ada@example.test', 'correct horse battery staple'),
    ])

    expect(api).toHaveBeenCalledTimes(2)
    expect(api).toHaveBeenNthCalledWith(1, 'auth/session/')
    expect(api).toHaveBeenNthCalledWith(2, 'auth/login/', {
      method: 'POST', data: { email: 'ada@example.test', password: 'correct horse battery staple' },
    })
  })
})
