import client from './client'

export const authApi = {
  register: (data) => client.post('/api/auth/register', data).then((r) => r.data),
  login: (data) => client.post('/api/auth/login', data).then((r) => r.data),
  me: () => client.get('/api/auth/me').then((r) => r.data),
}

export const projectApi = {
  list: () => client.get('/api/projects').then((r) => r.data),
  get: (id) => client.get(`/api/projects/${id}`).then((r) => r.data),
  create: (data) => client.post('/api/projects', data).then((r) => r.data),
  imagesets: (projectId) => client.get(`/api/projects/${projectId}/imagesets`).then((r) => r.data),
  getImageset: (projectId, id) =>
    client.get(`/api/projects/${projectId}/imagesets/${id}`).then((r) => r.data),
  addMember: (projectId, username) =>
    client.post(`/api/projects/${projectId}/members`, { username }).then((r) => r.data),
}

export const uploadApi = {
  createImageset: (projectId, { title, visible, ir, uv }, onProgress) => {
    const form = new FormData()
    form.append('title', title)
    form.append('visible', visible)
    if (ir) form.append('ir', ir)
    if (uv) form.append('uv', uv)
    return client
      .post(`/api/projects/${projectId}/imagesets`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (onProgress && event.total) onProgress(event.loaded / event.total)
        },
      })
      .then((r) => r.data)
  },
  reprocess: (projectId, imagesetId) =>
    client.post(`/api/projects/${projectId}/imagesets/${imagesetId}/reprocess`).then((r) => r.data),
}

export const annotationApi = {
  list: (imagesetId, baseVersion) =>
    client
      .get(`/api/imagesets/${imagesetId}/annotations`, {
        headers: baseVersion != null ? { 'X-Base-Version': baseVersion } : {},
      })
      .then((r) => r.data),
  create: (imagesetId, data, baseVersion) =>
    client
      .post(`/api/imagesets/${imagesetId}/annotations`, data, {
        headers: baseVersion != null ? { 'X-Base-Version': baseVersion } : {},
      })
      .then((r) => r.data),
  update: (imagesetId, id, data, baseVersion) =>
    client
      .patch(`/api/imagesets/${imagesetId}/annotations/${id}`, data, {
        headers: baseVersion != null ? { 'X-Base-Version': baseVersion } : {},
      })
      .then((r) => r.data),
  remove: (imagesetId, id, baseVersion) =>
    client
      .delete(`/api/imagesets/${imagesetId}/annotations/${id}`, {
        headers: baseVersion != null ? { 'X-Base-Version': baseVersion } : {},
      })
      .then((r) => r.data),
  versions: (imagesetId) =>
    client.get(`/api/imagesets/${imagesetId}/versions`).then((r) => r.data),
  commit: (imagesetId, comment) =>
    client.post(`/api/imagesets/${imagesetId}/versions`, null, { params: { comment } }).then((r) => r.data),
  rollback: (imagesetId, version, comment) =>
    client.post(`/api/imagesets/${imagesetId}/rollback`, { version, comment }).then((r) => r.data),
}
