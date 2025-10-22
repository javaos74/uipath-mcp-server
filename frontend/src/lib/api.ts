import axios from 'axios'
import type {
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  User,
  MCPServer,
  MCPServerCreate,
  MCPTool,
  MCPToolCreate,
  UiPathConfig,
} from '@/types'

// In production (built), use relative URL (same origin as backend)
// In development, use VITE_API_URL or default to localhost:8000
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  register: async (data: RegisterRequest): Promise<User> => {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post('/auth/login', data)
    return response.data
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  updateUiPathConfig: async (data: UiPathConfig): Promise<User> => {
    const response = await api.put('/auth/uipath-config', data)
    return response.data
  },
}

// Servers API
export const serversAPI = {
  list: async (): Promise<{ count: number; servers: MCPServer[] }> => {
    const response = await api.get('/api/servers')
    return response.data
  },

  create: async (data: MCPServerCreate): Promise<MCPServer> => {
    const response = await api.post('/api/servers', data)
    return response.data
  },

  get: async (tenantName: string, serverName: string): Promise<MCPServer> => {
    const response = await api.get(`/api/servers/${tenantName}/${serverName}`)
    return response.data
  },

  update: async (
    tenantName: string,
    serverName: string,
    data: Partial<MCPServerCreate>
  ): Promise<MCPServer> => {
    const response = await api.put(`/api/servers/${tenantName}/${serverName}`, data)
    return response.data
  },

  delete: async (tenantName: string, serverName: string): Promise<void> => {
    await api.delete(`/api/servers/${tenantName}/${serverName}`)
  },

  generateToken: async (
    tenantName: string,
    serverName: string
  ): Promise<{ token: string; message: string }> => {
    const response = await api.post(
      `/api/servers/${tenantName}/${serverName}/token`
    )
    return response.data
  },

  getToken: async (
    tenantName: string,
    serverName: string
  ): Promise<{ token: string | null; message?: string }> => {
    const response = await api.get(`/api/servers/${tenantName}/${serverName}/token`)
    return response.data
  },

  revokeToken: async (
    tenantName: string,
    serverName: string
  ): Promise<{ message: string }> => {
    const response = await api.delete(
      `/api/servers/${tenantName}/${serverName}/token`
    )
    return response.data
  },
}

// Tools API
export const toolsAPI = {
  list: async (
    tenantName: string,
    serverName: string
  ): Promise<{ count: number; tools: MCPTool[] }> => {
    const response = await api.get(`/api/servers/${tenantName}/${serverName}/tools`)
    return response.data
  },

  create: async (
    tenantName: string,
    serverName: string,
    data: MCPToolCreate
  ): Promise<MCPTool> => {
    const response = await api.post(
      `/api/servers/${tenantName}/${serverName}/tools`,
      data
    )
    return response.data
  },

  get: async (
    tenantName: string,
    serverName: string,
    toolName: string
  ): Promise<MCPTool> => {
    const response = await api.get(
      `/api/servers/${tenantName}/${serverName}/tools/${toolName}`
    )
    return response.data
  },

  update: async (
    tenantName: string,
    serverName: string,
    toolName: string,
    data: Partial<MCPToolCreate>
  ): Promise<MCPTool> => {
    const response = await api.put(
      `/api/servers/${tenantName}/${serverName}/tools/${toolName}`,
      data
    )
    return response.data
  },

  delete: async (
    tenantName: string,
    serverName: string,
    toolName: string
  ): Promise<void> => {
    await api.delete(`/api/servers/${tenantName}/${serverName}/tools/${toolName}`)
  },
}

// UiPath API
export const uipathAPI = {
  listFolders: async (q?: string): Promise<{ count: number; folders: any[]; matched?: any[]; matched_count?: number }> => {
    const url = q ? `/api/uipath/folders?q=${encodeURIComponent(q)}` : '/api/uipath/folders'
    const response = await api.get(url)
    return response.data
  },

  listProcesses: async (folderId: string): Promise<{ count: number; processes: any[] }> => {
    const response = await api.get(`/api/uipath/processes?folder_id=${folderId}`)
    return response.data
  },
}

export default api
