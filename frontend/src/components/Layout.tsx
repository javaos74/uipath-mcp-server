import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import './Layout.css'

export default function Layout() {
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
            UiPath MCP Manager
          </Link>
          
          <nav className="nav">
            <Link to="/" className="nav-link">Dashboard</Link>
            <Link to="/settings" className="nav-link">Settings</Link>
          </nav>

          <div className="user-menu">
            <span className="user-name">{user?.username}</span>
            <span className="user-role">{user?.role}</span>
            <button onClick={handleLogout} className="btn btn-secondary btn-sm">
              Logout
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
