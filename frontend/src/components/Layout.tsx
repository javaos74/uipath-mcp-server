import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './LanguageSwitcher'
import './Layout.css'

export default function Layout() {
  const { t } = useTranslation('auth')
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <div className="layout">
      <header className="header">
        <div className="container header-content">
          <Link to="/" className="logo">
            {t('common:app.title', { ns: 'common' })}
          </Link>
          
          <nav className="nav">
            <Link to="/" className="nav-link">{t('common:nav.dashboard', { ns: 'common' })}</Link>
            <Link to="/settings" className="nav-link">{t('common:nav.settings', { ns: 'common' })}</Link>
            {user?.role === 'admin' && (
              <Link to="/admin/builtin-tools" className="nav-link admin-link">
                🔧 {t('common:nav.builtinTools', { ns: 'common' })}
              </Link>
            )}
          </nav>

          <div className="user-menu">
            <LanguageSwitcher />
            <span className="user-name">{user?.username}</span>
            <span className="user-role">{user?.role}</span>
            <button onClick={handleLogout} className="btn btn-secondary btn-sm">
              {t('logout')}
            </button>
          </div>
        </div>
      </header>

      <main className="main">
        <div className="container">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
