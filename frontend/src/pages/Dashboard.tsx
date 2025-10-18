import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { serversAPI } from '@/lib/api'
import type { MCPServerCreate } from '@/types'
import './Dashboard.css'

export default function Dashboard() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['servers'],
    queryFn: serversAPI.list,
  })

  const deleteMutation = useMutation({
    mutationFn: ({ tenantName, serverName }: { tenantName: string; serverName: string }) =>
      serversAPI.delete(tenantName, serverName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
    },
  })

  const handleDelete = (tenantName: string, serverName: string) => {
    if (confirm(`Delete server ${tenantName}/${serverName}?`)) {
      deleteMutation.mutate({ tenantName, serverName })
    }
  }

  if (isLoading) {
    return <div className="loading"><div className="spinner" /></div>
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>MCP Servers</h1>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          + Create Server
        </button>
      </div>

      {data?.servers.length === 0 ? (
        <div className="empty-state">
          <p>No MCP servers yet. Create your first server to get started!</p>
        </div>
      ) : (
        <div className="servers-grid">
          {data?.servers.map((server) => (
            <div key={server.id} className="server-card">
              <div className="server-header">
                <h3>{server.server_name}</h3>
                <span className="server-tenant">{server.tenant_name}</span>
              </div>
              
              <p className="server-description">
                {server.description || 'No description'}
              </p>

              <div className="server-endpoint">
                <code>/mcp/{server.tenant_name}/{server.server_name}</code>
              </div>

              <div className="server-actions">
                <Link
                  to={`/servers/${server.tenant_name}/${server.server_name}`}
                  className="btn btn-primary btn-sm"
                >
                  Manage Tools
                </Link>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDelete(server.tenant_name, server.server_name)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateServerModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            queryClient.invalidateQueries({ queryKey: ['servers'] })
          }}
        />
      )}
    </div>
  )
}

function CreateServerModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess: () => void
}) {
  const [formData, setFormData] = useState<MCPServerCreate>({
    tenant_name: '',
    server_name: '',
    description: '',
  })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: serversAPI.create,
    onSuccess,
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Failed to create server')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Create MCP Server</h2>
        
        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>Tenant Name</label>
            <input
              type="text"
              className="input"
              value={formData.tenant_name}
              onChange={(e) =>
                setFormData({ ...formData, tenant_name: e.target.value })
              }
              required
            />
          </div>

          <div className="form-group">
            <label>Server Name</label>
            <input
              type="text"
              className="input"
              value={formData.server_name}
              onChange={(e) =>
                setFormData({ ...formData, server_name: e.target.value })
              }
              required
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              className="input"
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={3}
            />
          </div>

          {error && <div className="error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
