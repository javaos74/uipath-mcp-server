import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authAPI } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import './Auth.css'

export default function Login() {
  const { t } = useTranslation('auth')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await authAPI.login({ username, password })
      setAuth(response.user, response.access_token)
      navigate('/')
    } catch (err: any) {
      const serverError = err.response?.data?.error || ''
      // Map server error messages to translation keys
      if (serverError.includes('Invalid username or password')) {
        setError(t('login.error.invalidCredentials'))
      } else if (serverError.includes('pending')) {
        setError(t('login.error.pendingApproval'))
      } else {
        setError(t('login.error.failed'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">{t('login.title')}</h1>
        <p className="auth-subtitle">{t('common:app.title', { ns: 'common' })}</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">{t('login.username')}</label>
            <input
              id="username"
              type="text"
              className="input"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value)
                setError('')
              }}
              required
              autoFocus
              autoComplete="off"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">{t('login.password')}</label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                setError('')
              }}
              required
              autoComplete="new-password"
            />
          </div>

          {error && <div className="error">{error}</div>}

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={loading}
          >
            {loading ? `${t('login.button')}...` : t('login.button')}
          </button>
        </form>

        <p className="auth-footer">
          {t('login.noAccount')} <Link to="/register">{t('login.signUp')}</Link>
        </p>
      </div>
    </div>
  )
}
