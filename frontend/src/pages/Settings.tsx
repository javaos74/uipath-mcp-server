import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authAPI } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { UiPathConfig } from '@/types'
import './Settings.css'

export default function Settings() {
  const { user, updateUser } = useAuthStore()
  const [formData, setFormData] = useState<UiPathConfig>({
    uipath_url: user?.uipath_url || '',
    uipath_access_token: '',
    uipath_folder_path: user?.uipath_folder_path || '',
  })
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const updateMutation = useMutation({
    mutationFn: authAPI.updateUiPathConfig,
    onSuccess: (data) => {
      updateUser(data)
      setSuccess('UiPath configuration updated successfully')
      setError('')
      // Clear PAT field after successful update
      setFormData({ ...formData, uipath_access_token: '' })
    },
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Failed to update configuration')
      setSuccess('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  return (
    <div className="settings">
      <h1>Settings</h1>

      <div className="settings-section">
        <h2>User Information</h2>
        <div className="info-grid">
          <div className="info-item">
            <label>Username</label>
            <div>{user?.username}</div>
          </div>
          <div className="info-item">
            <label>Email</label>
            <div>{user?.email}</div>
          </div>
          <div className="info-item">
            <label>Role</label>
            <div className="user-role">{user?.role}</div>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h2>UiPath Configuration</h2>
        <p className="section-description">
          Configure your UiPath credentials. These will be used when executing RPA processes.
        </p>

        <form onSubmit={handleSubmit} className="settings-form">
          <div className="form-group">
            <label htmlFor="uipath_url">UiPath Cloud URL</label>
            <input
              id="uipath_url"
              type="text"
              className="input"
              placeholder="https://cloud.uipath.com/account/tenant"
              value={formData.uipath_url}
              onChange={(e) =>
                setFormData({ ...formData, uipath_url: e.target.value })
              }
            />
          </div>

          <div className="form-group">
            <label htmlFor="uipath_access_token">Personal Access Token (PAT)</label>
            <input
              id="uipath_access_token"
              type="password"
              className="input"
              placeholder="Enter your UiPath PAT"
              value={formData.uipath_access_token}
              onChange={(e) =>
                setFormData({ ...formData, uipath_access_token: e.target.value })
              }
            />
            <small className="form-help">
              Your PAT is stored securely and never displayed
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="uipath_folder_path">Default Folder Path</label>
            <input
              id="uipath_folder_path"
              type="text"
              className="input"
              placeholder="/Production/Finance"
              value={formData.uipath_folder_path}
              onChange={(e) =>
                setFormData({ ...formData, uipath_folder_path: e.target.value })
              }
            />
          </div>

          {success && <div className="success">{success}</div>}
          {error && <div className="error">{error}</div>}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Configuration'}
          </button>
        </form>
      </div>
    </div>
  )
}
