import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { serversAPI, toolsAPI, uipathAPI } from '@/lib/api'
import type { MCPTool, MCPToolCreate, UiPathProcess } from '@/types'
import './ServerDetail.css'

export default function ServerDetail() {
  const { tenantName, serverName } = useParams<{
    tenantName: string
    serverName: string
  }>()
  const [showProcessPicker, setShowProcessPicker] = useState(false)
  const [editingTool, setEditingTool] = useState<MCPTool | null>(null)
  const queryClient = useQueryClient()

  const { data: toolsData, isLoading } = useQuery({
    queryKey: ['tools', tenantName, serverName],
    queryFn: () => toolsAPI.list(tenantName!, serverName!),
    enabled: !!tenantName && !!serverName,
  })

  const deleteMutation = useMutation({
    mutationFn: (toolName: string) =>
      toolsAPI.delete(tenantName!, serverName!, toolName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools', tenantName, serverName] })
    },
  })

  const handleDelete = (toolName: string) => {
    if (confirm(`Delete tool ${toolName}?`)) {
      deleteMutation.mutate(toolName)
    }
  }

  if (isLoading) {
    return <div className="loading"><div className="spinner" /></div>
  }

  return (
    <div className="server-detail">
      <div className="detail-header">
        <div>
          <Link to="/" className="back-link">← Back to Dashboard</Link>
          <h1>{serverName}</h1>
          <p className="server-path">
            <code>/mcp/{tenantName}/{serverName}</code>
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowProcessPicker(true)}
        >
          + Add Tool from UiPath Process
        </button>
      </div>

      <TokenManager tenantName={tenantName!} serverName={serverName!} />

      {!toolsData?.tools || toolsData.tools.length === 0 ? (
        <div className="empty-state">
          <p>No tools yet. Add a tool from your UiPath processes!</p>
        </div>
      ) : (
        <div className="tools-list">
          {toolsData.tools.map((tool) => (
            <div key={tool.id} className="tool-card">
              <div className="tool-header">
                <h3>{tool.name}</h3>
                {tool.uipath_process_name && (
                  <div className="tool-badges">
                    <span className="tool-badge tool-badge-process">
                      Process: {tool.uipath_process_name}
                    </span>
                    {tool.uipath_folder_path && (
                      <span className="tool-badge tool-badge-folder">
                        Folder: {tool.uipath_folder_path}
                      </span>
                    )}
                  </div>
                )}
              </div>

              <p className="tool-description">{tool.description}</p>

              {tool.input_schema?.properties && (
                <div className="tool-params">
                  <h4>Parameters:</h4>
                  <ul>
                    {Object.entries(tool.input_schema.properties).map(([key, value]: [string, any]) => (
                      <li key={key}>
                        <div className="param-info">
                          <div className="param-name-line">
                            <code>{key}</code>
                            <span className="param-type">{value.type}</span>
                            {tool.input_schema.required?.includes(key) && (
                              <span className="param-required">required</span>
                            )}
                          </div>
                          {value.description && (
                            <div className="param-description">{value.description}</div>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="tool-actions">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setEditingTool(tool)}
                >
                  Edit
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDelete(tool.name)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showProcessPicker && (
        <UiPathProcessPicker
          tenantName={tenantName!}
          serverName={serverName!}
          onClose={() => setShowProcessPicker(false)}
          onSuccess={() => {
            setShowProcessPicker(false)
            queryClient.invalidateQueries({ queryKey: ['tools', tenantName, serverName] })
          }}
        />
      )}

      {editingTool && (
        <ToolEditor
          tenantName={tenantName!}
          serverName={serverName!}
          tool={editingTool}
          onClose={() => setEditingTool(null)}
          onSuccess={() => {
            setEditingTool(null)
            queryClient.invalidateQueries({ queryKey: ['tools', tenantName, serverName] })
          }}
        />
      )}
    </div>
  )
}

function UiPathProcessPicker({
  tenantName,
  serverName,
  onClose,
  onSuccess,
}: {
  tenantName: string
  serverName: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [selectedFolder, setSelectedFolder] = useState<any | null>(null)
  const [selectedProcess, setSelectedProcess] = useState<UiPathProcess | null>(null)
  const [toolName, setToolName] = useState('')
  const [toolDescription, setToolDescription] = useState('')
  const [parameters, setParameters] = useState<Array<{
    name: string
    type: string
    description: string
    required: boolean
  }>>([])
  const [error, setError] = useState('')

  const { data: foldersData, isLoading: foldersLoading, error: foldersError } = useQuery({
    queryKey: ['uipath-folders'],
    queryFn: uipathAPI.listFolders,
  })

  const { data: processesData, isLoading: processesLoading, error: processesError } = useQuery({
    queryKey: ['uipath-processes', selectedFolder?.id],
    queryFn: () => uipathAPI.listProcesses(selectedFolder!.id),
    enabled: !!selectedFolder,
  })

  const isLoading = foldersLoading || processesLoading
  const loadError = foldersError || processesError

  const createMutation = useMutation({
    mutationFn: (data: MCPToolCreate) => toolsAPI.create(tenantName, serverName, data),
    onSuccess,
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Failed to create tool')
    },
  })

  const handleSelectProcess = (process: UiPathProcess) => {
    setSelectedProcess(process)
    // Auto-fill tool name from process name (sanitize for MCP tool name)
    setToolName(process.name.toLowerCase().replace(/[^a-z0-9_]/g, '_'))
    // Auto-fill description
    setToolDescription(process.description || `Execute ${process.name}`)
    // Map input parameters
    setParameters(
      process.input_parameters.map((param) => ({
        name: param.name,
        type: param.type,
        description: param.description || `Parameter ${param.name}`,
        required: param.required,
      }))
    )
  }

  const handleCreateTool = () => {
    if (!selectedProcess || !toolName) {
      setError('Please select a process and enter a tool name')
      return
    }

    // Build input schema from edited parameters
    const properties: Record<string, any> = {}
    const required: string[] = []

    parameters.forEach((param) => {
      properties[param.name] = {
        type: param.type,
        description: param.description,
      }
      if (param.required) {
        required.push(param.name)
      }
    })

    const toolData: MCPToolCreate = {
      name: toolName,
      description: toolDescription,
      input_schema: {
        type: 'object',
        properties,
        required,
      },
      uipath_process_name: selectedProcess.name,
      uipath_folder_path: selectedFolder?.full_name || selectedFolder?.name || undefined,
      uipath_folder_id: selectedFolder?.id || undefined,
    }

    createMutation.mutate(toolData)
  }

  const handleParameterChange = (index: number, field: string, value: any) => {
    const newParams = [...parameters]
    newParams[index] = { ...newParams[index], [field]: value }
    setParameters(newParams)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
        <h2>Add Tool from UiPath Process</h2>

        {loadError && (
          <div className="error">
            {(loadError as any).response?.data?.error || 'Failed to load processes. Please check your UiPath configuration in Settings.'}
          </div>
        )}

        {isLoading ? (
          <div className="loading"><div className="spinner" /></div>
        ) : (
          <div className="process-picker">
            {!selectedFolder ? (
              <div className="folder-list">
                <h3>Step 1: Select a Folder</h3>
                {!foldersData?.folders || foldersData.folders.length === 0 ? (
                  <p className="empty-message">No folders found. Please check your UiPath configuration.</p>
                ) : (
                  <div className="folders">
                    {foldersData.folders.map((folder) => (
                      <div
                        key={folder.id}
                        className="folder-item"
                        onClick={() => setSelectedFolder(folder)}
                      >
                        <div className="folder-name">{folder.name}</div>
                        {folder.full_name && (
                          <div className="folder-path">{folder.full_name}</div>
                        )}
                        {folder.description && (
                          <div className="folder-description">{folder.description}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <>
                <div className="process-list">
                  <div className="step-header">
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setSelectedFolder(null)
                        setSelectedProcess(null)
                      }}
                    >
                      ← Change Folder
                    </button>
                    <h3>Step 2: Select a Process from {selectedFolder.name}</h3>
                  </div>
                  {!processesData?.processes || processesData.processes.length === 0 ? (
                    <p className="empty-message">No processes found in this folder.</p>
                  ) : (
                    <div className="processes">
                      {processesData.processes.map((process) => (
                        <div
                          key={process.id}
                          className={`process-item ${selectedProcess?.id === process.id ? 'selected' : ''}`}
                          onClick={() => handleSelectProcess(process)}
                        >
                          <div className="process-name">{process.name}</div>
                          <div className="process-version">v{process.version}</div>
                          {process.description && (
                            <div className="process-description">{process.description}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {selectedProcess && (
              <div className="process-details">
                <h3>Tool Configuration</h3>

                <div className="form-group">
                  <label>Tool Name *</label>
                  <input
                    type="text"
                    className="input"
                    value={toolName}
                    onChange={(e) => setToolName(e.target.value)}
                    placeholder="tool_name"
                    required
                  />
                  <small>Use lowercase letters, numbers, and underscores only</small>
                </div>

                <div className="form-group">
                  <label>UiPath Process</label>
                  <input
                    type="text"
                    className="input"
                    value={selectedProcess.name}
                    disabled
                  />
                </div>

                <div className="form-group">
                  <label>Tool Description *</label>
                  <textarea
                    className="input"
                    value={toolDescription}
                    onChange={(e) => setToolDescription(e.target.value)}
                    rows={2}
                    placeholder="Describe what this tool does..."
                    required
                  />
                </div>

                {parameters.length > 0 && (
                  <div className="form-group">
                    <label>Input Parameters ({parameters.length})</label>
                    <div className="params-editor">
                      {parameters.map((param, index) => (
                        <div key={param.name} className="param-editor-item">
                          <div className="param-header">
                            <div className="param-name-row">
                              <code>{param.name}</code>
                              <span className="param-type">{param.type}</span>
                              <label className="param-required-checkbox">
                                <input
                                  type="checkbox"
                                  checked={param.required}
                                  onChange={(e) =>
                                    handleParameterChange(index, 'required', e.target.checked)
                                  }
                                />
                                Required
                              </label>
                            </div>
                          </div>
                          <div className="param-description-row">
                            <input
                              type="text"
                              className="input input-sm"
                              value={param.description}
                              onChange={(e) =>
                                handleParameterChange(index, 'description', e.target.value)
                              }
                              placeholder="Parameter description..."
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {error && <div className="error">{error}</div>}

                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={onClose}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleCreateTool}
                    disabled={createMutation.isPending || !toolName || !toolDescription}
                  >
                    {createMutation.isPending ? 'Creating...' : 'Create Tool'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}


function ToolEditor({
  tenantName,
  serverName,
  tool,
  onClose,
  onSuccess,
}: {
  tenantName: string
  serverName: string
  tool: MCPTool
  onClose: () => void
  onSuccess: () => void
}) {
  const [toolDescription, setToolDescription] = useState(tool.description || '')
  const [parameters, setParameters] = useState<Array<{
    name: string
    type: string
    description: string
    required: boolean
  }>>([])
  const [error, setError] = useState('')

  // Initialize parameters from tool's input_schema
  useEffect(() => {
    if (tool.input_schema?.properties) {
      const params = Object.entries(tool.input_schema.properties).map(([key, value]: [string, any]) => ({
        name: key,
        type: value.type || 'string',
        description: value.description || '',
        required: tool.input_schema.required?.includes(key) || false,
      }))
      setParameters(params)
    }
  }, [tool])

  const updateMutation = useMutation({
    mutationFn: (data: Partial<MCPToolCreate>) =>
      toolsAPI.update(tenantName, serverName, tool.name, data),
    onSuccess,
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Failed to update tool')
    },
  })

  const handleParameterChange = (index: number, field: string, value: any) => {
    const newParams = [...parameters]
    newParams[index] = { ...newParams[index], [field]: value }
    setParameters(newParams)
  }

  const handleUpdate = () => {
    if (!toolDescription) {
      setError('Please enter a tool description')
      return
    }

    // Build input schema from edited parameters
    const properties: Record<string, any> = {}
    const required: string[] = []

    parameters.forEach((param: any) => {
      properties[param.name] = {
        type: param.type,
        description: param.description,
      }
      if (param.required) {
        required.push(param.name)
      }
    })

    const updateData: Partial<MCPToolCreate> = {
      description: toolDescription,
      input_schema: {
        type: 'object',
        properties,
        required,
      },
    }

    updateMutation.mutate(updateData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
        <h2>Edit Tool: {tool.name}</h2>

        <div className="tool-editor">
          <div className="form-group">
            <label>Tool Name</label>
            <input
              type="text"
              className="input"
              value={tool.name}
              disabled
            />
            <small>Tool name cannot be changed</small>
          </div>

          {tool.uipath_process_name && (
            <>
              <div className="form-group">
                <label>UiPath Process</label>
                <input
                  type="text"
                  className="input"
                  value={tool.uipath_process_name}
                  disabled
                />
              </div>

              {tool.uipath_folder_path && (
                <div className="form-group">
                  <label>UiPath Folder</label>
                  <input
                    type="text"
                    className="input"
                    value={tool.uipath_folder_path}
                    disabled
                  />
                </div>
              )}
            </>
          )}

          <div className="form-group">
            <label>Tool Description *</label>
            <textarea
              className="input"
              value={toolDescription}
              onChange={(e) => setToolDescription(e.target.value)}
              rows={3}
              placeholder="Describe what this tool does..."
              required
            />
          </div>

          {parameters.length > 0 && (
            <div className="form-group">
              <label>Input Parameters ({parameters.length})</label>
              <div className="params-editor">
                {parameters.map((param: any, index: number) => (
                  <div key={param.name} className="param-editor-item">
                    <div className="param-header">
                      <div className="param-name-row">
                        <code>{param.name}</code>
                        <span className="param-type">{param.type}</span>
                        <label className="param-required-checkbox">
                          <input
                            type="checkbox"
                            checked={param.required}
                            onChange={(e) =>
                              handleParameterChange(index, 'required', e.target.checked)
                            }
                          />
                          Required
                        </label>
                      </div>
                    </div>
                    <div className="param-description-row">
                      <input
                        type="text"
                        className="input input-sm"
                        value={param.description}
                        onChange={(e) =>
                          handleParameterChange(index, 'description', e.target.value)
                        }
                        placeholder="Parameter description..."
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <div className="error">{error}</div>}

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleUpdate}
              disabled={updateMutation.isPending || !toolDescription}
            >
              {updateMutation.isPending ? 'Updating...' : 'Update Tool'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


function TokenManager({
  tenantName,
  serverName,
}: {
  tenantName: string
  serverName: string
}) {
  const [token, setToken] = useState<string | null>(null)
  const [showToken, setShowToken] = useState(false)
  const [copied, setCopied] = useState(false)
  const queryClient = useQueryClient()

  const { data: tokenData, isLoading } = useQuery({
    queryKey: ['server-token', tenantName, serverName],
    queryFn: () => serversAPI.getToken(tenantName, serverName),
  })

  useEffect(() => {
    if (tokenData?.token) {
      setToken(tokenData.token)
    }
  }, [tokenData])

  const generateMutation = useMutation({
    mutationFn: () => serversAPI.generateToken(tenantName, serverName),
    onSuccess: (data) => {
      setToken(data.token)
      setShowToken(true)
      queryClient.invalidateQueries({ queryKey: ['server-token', tenantName, serverName] })
    },
  })

  const revokeMutation = useMutation({
    mutationFn: () => serversAPI.revokeToken(tenantName, serverName),
    onSuccess: () => {
      setToken(null)
      setShowToken(false)
      queryClient.invalidateQueries({ queryKey: ['server-token', tenantName, serverName] })
    },
  })

  const handleCopy = async () => {
    if (token) {
      await navigator.clipboard.writeText(token)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleGenerate = () => {
    if (token) {
      if (
        confirm(
          'Generating a new token will invalidate the existing token. Continue?'
        )
      ) {
        generateMutation.mutate()
      }
    } else {
      generateMutation.mutate()
    }
  }

  const handleRevoke = () => {
    if (confirm('Are you sure you want to revoke this token? This cannot be undone.')) {
      revokeMutation.mutate()
    }
  }

  if (isLoading) {
    return null
  }

  return (
    <div className="token-manager">
      <div className="token-header">
        <h3>API Token</h3>
        <p className="token-description">
          Use this token to connect external MCP clients to this server
        </p>
      </div>

      {token ? (
        <div className="token-content">
          <div className="token-display">
            <input
              type={showToken ? 'text' : 'password'}
              value={token}
              readOnly
              className="token-input"
            />
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowToken(!showToken)}
            >
              {showToken ? '👁️ Hide' : '👁️ Show'}
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleCopy}
              disabled={!showToken}
            >
              {copied ? '✓ Copied!' : '📋 Copy'}
            </button>
          </div>

          <div className="token-actions">
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? 'Generating...' : '🔄 Regenerate'}
            </button>
            <button
              className="btn btn-danger btn-sm"
              onClick={handleRevoke}
              disabled={revokeMutation.isPending}
            >
              {revokeMutation.isPending ? 'Revoking...' : '🗑️ Revoke'}
            </button>
          </div>

          <div className="token-usage">
            <h4>How to use:</h4>
            <div className="usage-example">
              <p>Method 1: Authorization Header (Recommended)</p>
              <code>
                curl -N -H "Authorization: Bearer {token.substring(0, 20)}..." <br />
                http://localhost:8000/mcp/{tenantName}/{serverName}
              </code>
            </div>
            <div className="usage-example">
              <p>Method 2: Query Parameter</p>
              <code>
                curl -N http://localhost:8000/mcp/{tenantName}/{serverName}?token=
                {token.substring(0, 20)}...
              </code>
            </div>
          </div>
        </div>
      ) : (
        <div className="token-empty">
          <p>No API token generated yet</p>
          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? 'Generating...' : '🔑 Generate Token'}
          </button>
        </div>
      )}
    </div>
  )
}
