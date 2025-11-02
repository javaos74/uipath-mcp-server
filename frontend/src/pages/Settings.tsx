import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { authAPI } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { UiPathConfig } from '@/types'
import './Settings.css'

type AuthType = 'pat' | 'oauth'

export default function Settings() {
  const { t } = useTranslation('settings')
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
      // Sync local UI state with latest server values
      setAuthType((data?.uipath_auth_type as AuthType) || 'pat')
      setFormData((prev) => ({ ...prev, uipath_url: data?.uipath_url || '' }))
      // Handle different success/error scenarios
      if (data?.message) {
        // Backend provided a specific message (usually an error or warning)
        if (data.message.includes('failed') || data.message.includes('error')) {
          setError(data.message)
          setSuccess('')
        } else {
          setSuccess(data.message)
          setError('')
        }
      } else if (authType === 'oauth' && !data?.has_uipath_token) {
        setError(t('uipath.message.oauthFailed'))
        setSuccess('')
      } else if (data?.has_uipath_token || authType === 'pat') {
        setSuccess(t('uipath.message.success'))
        setError('')
      } else {
        setSuccess(t('uipath.message.saved'))
        setError('')
      }
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
        uipath_client_id: '',
        uipath_client_secret: '',
      }
      
      // Only include PAT if it's not empty (user wants to update it)
      if (formData.uipath_access_token) {
        payload.uipath_access_token = formData.uipath_access_token
      }
      
      console.log('Submitting PAT config:', payload)
      updateMutation.mutate(payload)
    } else {
      // OAuth mode: send OAuth credentials, clear PAT
      const payload: UiPathConfig = {
        uipath_url: formData.uipath_url,
        uipath_auth_type: 'oauth',
        uipath_access_token: '',
        uipath_client_id: oauthData.client_id || '',
        uipath_client_secret: oauthData.client_secret || '',
      }
      
      console.log('Submitting OAuth config:', {
        ...payload,
        uipath_client_secret: payload.uipath_client_secret ? '***' : ''
      })
      updateMutation.mutate(payload)
    }
  }

  return (
    <div className="settings">
      <h1>{t('title')}</h1>

      <div className="settings-section">
        <h2>{t('userInfo.title')}</h2>
        <div className="info-grid">
          <div className="info-item">
            <label>{t('userInfo.username')}</label>
            <div>{user?.username}</div>
          </div>
          <div className="info-item">
            <label>{t('userInfo.email')}</label>
            <div>{user?.email}</div>
          </div>
          <div className="info-item">
            <label>{t('userInfo.role')}</label>
            <div className="user-role">{user?.role}</div>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h2>{t('uipath.title')}</h2>
        <p className="section-description">
          {t('uipath.description')}
        </p>

        <form onSubmit={handleSubmit} className="settings-form">
          <div className="form-group">
            <label htmlFor="uipath_url">{t('uipath.url.label')}</label>
            <input
              id="uipath_url"
              type="text"
              className="input"
              placeholder={t('uipath.url.placeholder')}
              value={formData.uipath_url}
              onChange={(e) =>
                setFormData({ ...formData, uipath_url: e.target.value })
              }
            />
            <small className="form-help">
              <strong>{t('uipath.url.help.title')}</strong><br />
              • <strong>{t('uipath.url.help.msi')}</strong><br />
              • <strong>{t('uipath.url.help.suite')}</strong>
            </small>
          </div>

          <div className="form-group">
            <label>{t('uipath.authType.label')}</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="authType"
                  value="pat"
                  checked={authType === 'pat'}
                  onChange={(e) => setAuthType(e.target.value as AuthType)}
                />
                <span>{t('uipath.authType.pat')}</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="authType"
                  value="oauth"
                  checked={authType === 'oauth'}
                  onChange={(e) => setAuthType(e.target.value as AuthType)}
                />
                <span>{t('uipath.authType.oauth')}</span>
              </label>
            </div>
          </div>

          {authType === 'pat' ? (
            <div className="form-group">
              <label htmlFor="uipath_access_token">{t('uipath.pat.label')}</label>
              <input
                id="uipath_access_token"
                type="password"
                className="input"
                placeholder={
                  user?.has_uipath_token
                    ? t('uipath.pat.placeholderExists')
                    : t('uipath.pat.placeholder')
                }
                value={formData.uipath_access_token}
                onChange={(e) =>
                  setFormData({ ...formData, uipath_access_token: e.target.value })
                }
              />
              <small className="form-help">
                {user?.has_uipath_token
                  ? t('uipath.pat.helpExists')
                  : t('uipath.pat.help')}
              </small>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label htmlFor="client_id">{t('uipath.oauth.clientId.label')}</label>
                <input
                  id="client_id"
                  type="text"
                  className="input"
                  placeholder={
                    user?.uipath_client_id
                      ? user.uipath_client_id
                      : t('uipath.oauth.clientId.placeholder')
                  }
                  value={oauthData.client_id}
                  onChange={(e) =>
                    setOauthData({ ...oauthData, client_id: e.target.value })
                  }
                />
                <small className="form-help">
                  {user?.uipath_client_id
                    ? t('uipath.oauth.clientId.helpExists', { clientId: user.uipath_client_id })
                    : t('uipath.oauth.clientId.help')}
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="client_secret">{t('uipath.oauth.clientSecret.label')}</label>
                <input
                  id="client_secret"
                  type="password"
                  className="input"
                  placeholder={
                    user?.has_oauth_credentials
                      ? t('uipath.oauth.clientSecret.placeholderExists')
                      : t('uipath.oauth.clientSecret.placeholder')
                  }
                  value={oauthData.client_secret}
                  onChange={(e) =>
                    setOauthData({ ...oauthData, client_secret: e.target.value })
                  }
                />
                <small className="form-help">
                  {user?.has_oauth_credentials
                    ? t('uipath.oauth.clientSecret.helpExists')
                    : t('uipath.oauth.clientSecret.help')}
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
            {updateMutation.isPending ? t('uipath.button.saving') : t('uipath.button.save')}
          </button>
        </form>
      </div>
    </div>
  )
}
