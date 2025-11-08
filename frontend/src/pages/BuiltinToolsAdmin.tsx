import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { builtinToolsAPI } from '@/lib/api'
import type { BuiltinTool } from '@/types'
import './BuiltinToolsAdmin.css'

export default function BuiltinToolsAdmin() {
  const { t } = useTranslation('admin')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingTool, setEditingTool] = useState<BuiltinTool | null>(null)
  const queryClient = useQueryClient()

  const { data: toolsData, isLoading } = useQuery({
    queryKey: ['builtin-tools-admin'],
    queryFn: () => builtinToolsAPI.list(false), // Show all tools including inactive
  })

  const deleteMutation = useMutation({
    mutationFn: (toolId: number) => builtinToolsAPI.delete(toolId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['builtin-tools-admin'] })
      queryClient.invalidateQueries({ queryKey: ['builtin-tools'] })
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ toolId, isActive }: { toolId: number; isActive: boolean }) =>
      builtinToolsAPI.update(toolId, { is_active: !isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['builtin-tools-admin'] })
      queryClient.invalidateQueries({ queryKey: ['builtin-tools'] })
    },
  })

  const handleDelete = (tool: BuiltinTool) => {
    if (confirm(t('confirmDelete', { name: tool.name }))) {
      deleteMutation.mutate(tool.id)
    }
  }

  const handleToggleActive = (tool: BuiltinTool) => {
    toggleActiveMutation.mutate({ toolId: tool.id, isActive: tool.is_active })
  }

  if (isLoading) {
    return <div className="loading"><div className="spinner" /></div>
  }

  return (
    <div className="builtin-tools-admin">
      <div className="admin-header">
        <div>
          <Link to="/" className="back-link">← {t('backToDashboard')}</Link>
          <h1>{t('title')}</h1>
          <p className="subtitle">{t('subtitle')}</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          + {t('createButton')}
        </button>
      </div>

      {!toolsData?.tools || toolsData.tools.length === 0 ? (
        <div className="empty-state">
          <p>{t('empty')}</p>
        </div>
      ) : (
        <div className="tools-grid">
          {toolsData.tools.map((tool: BuiltinTool) => (
            <div key={tool.id} className="tool-card">
              <div className="tool-card-header">
                <div className="tool-title">
                  <h3>{tool.name}</h3>
                  <span className={`status-badge ${tool.is_active ? 'active' : 'inactive'}`}>
                    {tool.is_active ? t('status.active') : t('status.inactive')}
                  </span>
                </div>
                <div className="tool-actions">
                  <button
                    className="btn-icon"
                    onClick={() => handleToggleActive(tool)}
                    title={tool.is_active ? t('action.deactivate') : t('action.activate')}
                  >
                    {tool.is_active ? '⏸️' : '▶️'}
                  </button>
                  <button
                    className="btn-icon"
                    onClick={() => setEditingTool(tool)}
                    title={t('action.edit')}
                  >
                    ✏️
                  </button>
                  <button
                    className="btn-icon btn-danger"
                    onClick={() => handleDelete(tool)}
                    title={t('action.delete')}
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <p className="tool-description">{tool.description}</p>

              <div className="tool-meta">
                <div className="meta-item">
                  <span className="meta-label">{t('field.function')}:</span>
                  <code>{tool.python_function}</code>
                </div>
                {tool.api_key && (
                  <div className="meta-item">
                    <span className="meta-label">{t('field.apiKey')}:</span>
                    <code className="masked">{'*'.repeat(20)}</code>
                  </div>
                )}
                {tool.input_schema?.properties && (
                  <div className="meta-item">
                    <span className="meta-label">{t('field.parameters')}:</span>
                    <span>{Object.keys(tool.input_schema.properties).length}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <BuiltinToolForm
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            queryClient.invalidateQueries({ queryKey: ['builtin-tools-admin'] })
            queryClient.invalidateQueries({ queryKey: ['builtin-tools'] })
          }}
        />
      )}

      {editingTool && (
        <BuiltinToolForm
          tool={editingTool}
          onClose={() => setEditingTool(null)}
          onSuccess={() => {
            setEditingTool(null)
            queryClient.invalidateQueries({ queryKey: ['builtin-tools-admin'] })
            queryClient.invalidateQueries({ queryKey: ['builtin-tools'] })
          }}
        />
      )}
    </div>
  )
}

function BuiltinToolForm({
  tool,
  onClose,
  onSuccess,
}: {
  tool?: BuiltinTool
  onClose: () => void
  onSuccess: () => void
}) {
  const { t } = useTranslation('admin')
  const [name, setName] = useState(tool?.name || '')
  const [description, setDescription] = useState(tool?.description || '')
  const [pythonFunction, setPythonFunction] = useState(tool?.python_function || '')
  const [apiKey, setApiKey] = useState(tool?.api_key || '')
  const [inputSchema, setInputSchema] = useState(
    JSON.stringify(tool?.input_schema || { type: 'object', properties: {}, required: [] }, null, 2)
  )
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: async (data: any) => {
      if (tool) {
        return builtinToolsAPI.update(tool.id, data)
      } else {
        return builtinToolsAPI.create(data)
      }
    },
    onSuccess,
    onError: (err: any) => {
      setError(err.response?.data?.error || t('form.error.saveFailed'))
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate JSON schema
    let parsedSchema
    try {
      parsedSchema = JSON.parse(inputSchema)
    } catch (err) {
      setError(t('form.error.invalidJson'))
      return
    }

    const data: any = {
      description,
      input_schema: parsedSchema,
      python_function: pythonFunction,
      api_key: apiKey || null,
    }

    if (!tool) {
      data.name = name
    }

    mutation.mutate(data)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
        <h2>{tool ? t('form.titleEdit', { name: tool.name }) : t('form.titleCreate')}</h2>

        <form onSubmit={handleSubmit} className="builtin-form">
          <div className="form-group">
            <label>{t('form.field.name')} *</label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!!tool}
              required
            />
            {tool && <small>{t('form.field.nameHelp')}</small>}
          </div>

          <div className="form-group">
            <label>{t('form.field.description')} *</label>
            <textarea
              className="input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              required
            />
          </div>

          <div className="form-group">
            <label>{t('form.field.pythonFunction')} *</label>
            <input
              type="text"
              className="input"
              value={pythonFunction}
              onChange={(e) => setPythonFunction(e.target.value)}
              placeholder="module.function_name"
              required
            />
            <small>{t('form.field.pythonFunctionHelp')}</small>
          </div>

          <div className="form-group">
            <label>{t('form.field.apiKey')}</label>
            <input
              type="password"
              className="input"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={t('form.field.apiKeyPlaceholder')}
            />
            <small>{t('form.field.apiKeyHelp')}</small>
          </div>

          <div className="form-group">
            <label>{t('form.field.inputSchema')} *</label>
            <textarea
              className="input code"
              value={inputSchema}
              onChange={(e) => setInputSchema(e.target.value)}
              rows={12}
              required
              style={{ fontFamily: 'monospace', fontSize: '13px' }}
            />
            <small>{t('form.field.inputSchemaHelp')}</small>
          </div>

          {error && <div className="error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              {t('common:button.cancel', { ns: 'common' })}
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={mutation.isPending}
            >
              {mutation.isPending
                ? t('form.button.saving')
                : tool
                ? t('form.button.update')
                : t('form.button.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
