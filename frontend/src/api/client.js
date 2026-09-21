const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    let detail
    try {
      detail = await res.json()
    } catch {
      detail = { message: res.statusText }
    }
    const err = new Error(detail?.detail?.message || detail?.message || res.statusText)
    err.status = res.status
    err.detail = detail?.detail
    throw err
  }
  return res.json()
}

export const api = {
  listProjects: () => request('/projects'),
  createProject: (payload) =>
    request('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  uploadBand: (projectId, band, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/projects/${projectId}/images?band=${band}`, {
      method: 'POST',
      body: form,
    })
  },
  listSets: (projectId) => request(`/projects/${projectId}/sets`),
  register: (imageSetId) => request(`/sets/${imageSetId}/register`, { method: 'POST' }),
  getAnnotations: (imageSetId) => request(`/sets/${imageSetId}/annotations`),
  pollAnnotations: (imageSetId, since) =>
    request(`/sets/${imageSetId}/annotations/poll?since=${since}`),
  saveAnnotations: (imageSetId, payload) =>
    request(`/sets/${imageSetId}/annotations/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  listVersions: (imageSetId) => request(`/sets/${imageSetId}/annotations/versions`),
  rollback: (imageSetId, payload) =>
    request(`/sets/${imageSetId}/annotations/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
}
