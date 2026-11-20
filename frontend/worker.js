export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    if (url.pathname.startsWith('/api/')) {
      const backend = new URL(env.API_ORIGIN)

      backend.pathname = url.pathname
      backend.search = url.search

      return fetch(new Request(backend, request), {
        redirect: 'manual',
      })
    }

    return env.ASSETS.fetch(request)
  },
}