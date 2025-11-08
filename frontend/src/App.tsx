import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Dashboard from '@/pages/Dashboard'
import ServerDetail from '@/pages/ServerDetail'
import Settings from '@/pages/Settings'
import BuiltinToolsAdmin from '@/pages/BuiltinToolsAdmin'
import UsersAdmin from '@/pages/UsersAdmin'
import Layout from '@/components/Layout'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }
  
  if (user?.role !== 'admin') {
    return <Navigate to="/" />
  }
  
  return <>{children}</>
}

function RoleBasedHome() {
  const user = useAuthStore((state) => state.user)
  
  if (user?.role === 'admin') {
    return <Navigate to="/admin/users" replace />
  }
  
  return <Dashboard />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<RoleBasedHome />} />
        <Route path="servers/:tenantName/:serverName" element={<ServerDetail />} />
        <Route path="settings" element={<Settings />} />
        <Route
          path="admin/users"
          element={
            <AdminRoute>
              <UsersAdmin />
            </AdminRoute>
          }
        />
        <Route
          path="admin/builtin-tools"
          element={
            <AdminRoute>
              <BuiltinToolsAdmin />
            </AdminRoute>
          }
        />
      </Route>
    </Routes>
  )
}

export default App
