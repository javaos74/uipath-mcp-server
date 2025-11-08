export interface User {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
  is_active: boolean
  uipath_url: string | null
  uipath_auth_type?: 'pat' | 'oauth'
  uipath_client_id?: string | null
  has_uipath_token: boolean
  has_oauth_credentials: boolean
  created_at: string
  updated_at: string
  // Optional informational message from certain endpoints (e.g., config update)
  message?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  role?: 'user' | 'admin'
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface MCPServer {
  id: number
  tenant_name: string
  server_name: string
  description: string | null
  user_id: number
  created_at: string
  updated_at: string
}

export interface MCPServerCreate {
  tenant_name: string
  server_name: string
  description?: string
}

export interface MCPTool {
  id: number
  server_id: number
  name: string
  description: string
  input_schema: Record<string, any>
  tool_type: 'uipath' | 'builtin'
  uipath_process_name: string | null
  uipath_process_key: string | null
  uipath_folder_path: string | null
  uipath_folder_id: string | null
  builtin_tool_id: number | null
  created_at: string
  updated_at: string
}

export interface MCPToolCreate {
  name: string
  description: string
  input_schema: Record<string, any>
  tool_type?: 'uipath' | 'builtin'
  uipath_process_name?: string
  uipath_process_key?: string
  uipath_folder_path?: string
  uipath_folder_id?: string
  builtin_tool_id?: number
}

export interface BuiltinTool {
  id: number
  name: string
  description: string
  input_schema: Record<string, any>
  python_function: string
  api_key: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UiPathConfig {
  uipath_url?: string
  uipath_auth_type?: 'pat' | 'oauth'
  uipath_access_token?: string
  uipath_client_id?: string
  uipath_client_secret?: string
}

export interface UiPathFolder {
  id: string
  name: string
  full_name: string
  description: string
  type: string
}

export interface UiPathProcess {
  id: string
  name: string
  description: string
  version: string
  key: string
  input_parameters: Array<{
    name: string
    type: string
    description: string
    required: boolean
  }>
}
