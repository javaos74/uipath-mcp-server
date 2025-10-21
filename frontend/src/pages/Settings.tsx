import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authAPI } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { UiPathConfig } from '@/types'
import './Settings.css'

type AuthType = 'pat' | 'oauth'

export default function Settings() {
  const { user, updateUser } = useAuthStore()
  const [authType, setAuthType] = useState<AuthType>(user?.uipath_auth_type || 'pat')
  const [formData, setFormData] = useState<UiPathConfig>({
    uipath_url: user?.uipath_url || '',
    uipath_access_token: '',
  })
  const [oauthData, setOauthData] = useState({
    client_id: '',
    client_secret: '',
  })
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const updateMutation = useMutation({
    mutationFn: authAPI.updateUiPathConfig,
    onSuccess: (data) => {
      updateUser(data)
      setSuccess('UiPath configuration updated successfully')
      setError('')
      // Clear sensitive fields after successful update
      setFormData({ ...formData, uipath_access_token: '' })
      setOauthData({ client_id: '', client_secret: '' })
    },
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Failed to update configuration')
      setSuccess('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (authType === 'pat') {
      // PAT mode: send PAT, clear OAuth fields
      const payload: UiPathConfig = {
        uipath_url: formData.uipath_url,
        uipath_auth_type: 'pat',
      }
      
      // Only include PAT if it's not empty (user wants to update it)
      if (formData.uipath_access_token) {
        payload.uipath_access_token = formData.uipath_access_token
      }
      
      // Clear OAuth credentials when switching to PAT
      payload.uipath_client_id = ''
      payload.uipath_client_secret = ''
      
      updateMutation.mutate(payload)
    } else {
      // OAuth mode: send OAuth credentials, clear PAT
      const payload: UiPathConfig = {
        uipath_url: formData.uipath_url,
        uipath_auth_type: 'oauth',
      }
      
      // Only include OAuth fields if they're not empty
      if (oauthData.client_id) {
        payload.uipath_client_id = oauthData.client_id
      }
      if (oauthData.client_secret) {
        payload.uipath_client_secret = oauthData.client_secret
      }
      
      // Clear PAT when switching to OAuth
      payload.uipath_access_token = ''
      
      updateMutation.mutate(payload)
    }
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
            <label htmlFor="uipath_url">UiPath Cloud/Automation Suite URL</label>
            <input
              id="uipath_url"
              type="text"
              className="input"
              placeholder="https://cloud.uipath.com/org_name/tenant_name"
              value={formData.uipath_url}
              onChange={(e) =>
                setFormData({ ...formData, uipath_url: e.target.value })
              }
            />
          </div>

          <div className="form-group">
            <label>Authentication Type</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="authType"
                  value="pat"
                  checked={authType === 'pat'}
                  onChange={(e) => setAuthType(e.target.value as AuthType)}
                />
                <span>Personal Access Token (PAT)</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="authType"
                  value="oauth"
                  checked={authType === 'oauth'}
                  onChange={(e) => setAuthType(e.target.value as AuthType)}
                />
                <span>OAuth 2.0 (Client Credentials)</span>
              </label>
            </div>
          </div>

          {authType === 'pat' ? (
            <div className="form-group">
              <label htmlFor="uipath_access_token">UiPath Personal Access Token (PAT)</label>
              <input
                id="uipath_access_token"
                type="password"
                className="input"
                placeholder={
                  user?.has_uipath_token
                    ? '••••••••••••••••'
                    : 'No PAT found - Enter your UiPath PAT'
                }
                value={formData.uipath_access_token}
                onChange={(e) =>
                  setFormData({ ...formData, uipath_access_token: e.target.value })
                }
              />
              <small className="form-help">
                {user?.has_uipath_token
                  ? 'Current: ••••••••••••••••  (stored securely)'
                  : 'No PAT configured. Your PAT will be stored securely.'}
              </small>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label htmlFor="client_id">OAuth Client ID</label>
                <input
                  id="client_id"
                  type="text"
                  className="input"
                  placeholder={
                    user?.uipath_client_id
                      ? user.uipath_client_id
                      : 'Enter your OAuth Client ID'
                  }
                  value={oauthData.client_id}
                  onChange={(e) =>
                    setOauthData({ ...oauthData, client_id: e.target.value })
                  }
                />
                <small className="form-help">
                  {user?.uipath_client_id
                    ? `Current: ${user.uipath_client_id}`
                    : 'The Client ID from your UiPath OAuth application'}
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="client_secret">OAuth Client Secret</label>
                <input
                  id="client_secret"
                  type="password"
                  className="input"
                  placeholder={
                    user?.has_oauth_credentials
                      ? '••••••••••••••••'
                      : 'Enter your OAuth Client Secret'
                  }
                  value={oauthData.client_secret}
                  onChange={(e) =>
                    setOauthData({ ...oauthData, client_secret: e.target.value })
                  }
                />
                <small className="form-help">
                  {user?.has_oauth_credentials
                    ? 'Current: ••••••••••••••••  (stored securely)'
                    : 'The Client Secret will be stored securely and used to obtain access tokens'}
                </small>
              </div>
            </>
          )}

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
