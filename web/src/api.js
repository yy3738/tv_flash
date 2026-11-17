const BASE = ''

async function api(path, opts = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body.detail || res.statusText || ('HTTP ' + res.status))
  }
  return body
}

export const login = (username, password) =>
  api('/api/login', { method: 'POST', body: JSON.stringify({ username, password }) })

export const logout = () => api('/api/logout', { method: 'POST' })

export const listDevices = () => api('/api/devices')

export const createDevice = (name) =>
  api('/api/devices', { method: 'POST', body: JSON.stringify({ name }) })

export const kickDevice = (id) =>
  api(`/api/devices/${id}/kick`, { method: 'POST' })

export const deleteDevice = (id) =>
  api(`/api/devices/${id}`, { method: 'DELETE' })
