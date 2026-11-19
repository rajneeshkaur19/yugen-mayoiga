const API_BASE_URL = '/api'

export function getToken() {
  return localStorage.getItem('yugen_access_token')
}

export function setToken(token) {
  localStorage.setItem('yugen_access_token', token)
}

export function clearToken() {
  localStorage.removeItem('yugen_access_token')
}

async function request(endpoint, options = {}) {
  const token = getToken()
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message = typeof data?.detail === 'string'
      ? data.detail
      : `Request failed (${response.status})`
    throw new Error(message)
  }

  return data
}

export const authApi = {
  register: (userData) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(userData),
  }),

  login: async (credentials) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })
    setToken(data.access_token)
    return data
  },

  forgotPassword: (email) => request('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  }),

  resetPassword: (token, newPassword) => request('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  }),

  me: () => request('/auth/me'),
  logout: () => clearToken(),
}

export const storiesApi = {
  list: () => request('/stories'),
  get: (storyId) => request(`/stories/${storyId}`),
  create: (storyData) => request('/stories', {
    method: 'POST',
    body: JSON.stringify(storyData),
  }),
  delete: (storyId) => request(`/stories/${storyId}`, {
    method: 'DELETE',
  }),
}

export const scenesApi = {
  list: (storyId) => request(`/stories/${storyId}/scenes`),
  create: (storyId, sceneData) => request(`/stories/${storyId}/scenes`, {
    method: 'POST',
    body: JSON.stringify(sceneData),
  }),
}

export const choicesApi = {
  list: (storyId, sceneId) =>
    request(`/stories/${storyId}/scenes/${sceneId}/choices`),

  create: (storyId, sceneId, choiceData) =>
    request(`/stories/${storyId}/scenes/${sceneId}/choices`, {
      method: 'POST',
      body: JSON.stringify(choiceData),
    }),
}

export const stateApi = {
  get: (storyId) => request(`/stories/${storyId}/state`),
  getYugenMeter: (storyId) => request(`/stories/${storyId}/yugen-meter`),
}

export const actionApi = {
  submitChoice: (storyId, actionData) => request(`/stories/${storyId}/choice`, {
    method: 'POST',
    body: JSON.stringify(actionData),
  }),
}

export const charactersApi = {
  list: (storyId) => request(`/stories/${storyId}/characters`),
}

export const memoriesApi = {
  list: (storyId, characterId) =>
    request(`/stories/${storyId}/memories${characterId ? `?character_id=${characterId}` : ''}`),
  create: (storyId, memoryData) =>
    request(`/stories/${storyId}/memories`, {
      method: 'POST',
      body: JSON.stringify(memoryData),
    }),
}

export const endingsApi = {
  list: (storyId) => request(`/stories/${storyId}/endings`),
}

export const aiApi = {
  generateLocationImage: (data) =>
    request('/ai/generate-location-image', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}





