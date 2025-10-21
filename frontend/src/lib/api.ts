import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

// Add request interceptor to include auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth data and redirect to login
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  login: async (data: { username: string; password: string }) => {
    const response = await api.post('/auth/login', data)
    return response.data
  },
  register: async (data: { username: string; password: string; email: string }) => {
    const response = await api.post('/auth/register', data)
    return response.data
  },
  updateUiPathConfig: async (config: any) => {
    const response = await api.put('/auth/uipath-config', config)
    return response.data
  },
}

export const serversAPI = {
  list: async () => {
    const response = await api.get('/api/servers')
    return response.data
  },
  create: async (data: any) => {
    const response = await api.post('/api/servers', data)
    return response.data
  },
  delete: async (tenantName: string, serverName: string) => {
    const response = await api.delete(`/api/servers/${tenantName}/${serverName}`)
    return response.data
  },
  getToken: async (tenantName: string, serverName: string) => {
    const response = await api.get(`/api/servers/${tenantName}/${serverName}/token`)
    return response.data
  },
  generateToken: async (tenantName: string, serverName: string) => {
    const response = await api.post(`/api/servers/${tenantName}/${serverName}/token`)
    return response.data
  },
  revokeToken: async (tenantName: string, serverName: string) => {
    const response = await api.delete(`/api/servers/${tenantName}/${serverName}/token`)
    return response.data
  },
}

export const toolsAPI = {
  list: async (tenantName: string, serverName: string) => {
    const response = await api.get(`/api/servers/${tenantName}/${serverName}/tools`)
    return response.data
  },
  create: async (tenantName: string, serverName: string, toolData: any) => {
    const response = await api.post(`/api/servers/${tenantName}/${serverName}/tools`, toolData)
    return response.data
  },
  update: async (tenantName: string, serverName: string, toolId: string, toolData: any) => {
    const response = await api.put(`/api/servers/${tenantName}/${serverName}/tools/${toolId}`, toolData)
    return response.data
  },
  delete: async (tenantName: string, serverName: string, toolId: string) => {
    const response = await api.delete(`/api/servers/${tenantName}/${serverName}/tools/${toolId}`)
    return response.data
  },
}

export const uipathAPI = {
  listFolders: async () => {
    const response = await api.get('/api/uipath/folders')
    return response.data
  },
  listProcesses: async (folderId: string) => {
    const response = await api.get(`/api/uipath/processes?folderId=${folderId}`)
    return response.data
  },
}
