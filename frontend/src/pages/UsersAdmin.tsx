import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store/authStore'
import api from '@/lib/api'
import './UsersAdmin.css'

interface User {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
  is_active: boolean
  created_at: string
}

export default function UsersAdmin() {
  const { t } = useTranslation('admin')
  const currentUser = useAuthStore((state) => state.user)
  const queryClient = useQueryClient()

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['users-admin'],
    queryFn: async () => {
      const response = await api.get('/api/admin/users')
      return response.data
    },
  })

  const approveMutation = useMutation({
    mutationFn: async (userId: number) => {
      await api.post(`/api/admin/users/${userId}/approve`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users-admin'] })
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: async (userId: number) => {
      await api.post(`/api/admin/users/${userId}/deactivate`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users-admin'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (userId: number) => {
      await api.delete(`/api/admin/users/${userId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users-admin'] })
    },
  })

  const handleApprove = (user: User) => {
    if (confirm(t('users.confirmApprove', { username: user.username }))) {
      approveMutation.mutate(user.id)
    }
  }

  const handleDeactivate = (user: User) => {
    if (user.id === currentUser?.id) {
      alert(t('users.error.cannotDeactivateSelf'))
      return
    }
    if (confirm(t('users.confirmDeactivate', { username: user.username }))) {
      deactivateMutation.mutate(user.id)
    }
  }

  const handleDelete = (user: User) => {
    if (user.id === currentUser?.id) {
      alert(t('users.error.cannotDeleteSelf'))
      return
    }
    if (confirm(t('users.confirmDelete', { username: user.username }))) {
      deleteMutation.mutate(user.id)
    }
  }

  if (isLoading) {
    return <div className="loading"><div className="spinner" /></div>
  }

  return (
    <div className="users-admin">
      <div className="admin-header">
        <div>
          <h1>{t('users.title')}</h1>
          <p className="subtitle">{t('users.subtitle')}</p>
        </div>
      </div>

      {!usersData?.users || usersData.users.length === 0 ? (
        <div className="empty-state">
          <p>{t('users.empty')}</p>
        </div>
      ) : (
        <div className="users-table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>{t('users.table.username')}</th>
                <th>{t('users.table.email')}</th>
                <th>{t('users.table.role')}</th>
                <th>{t('users.table.status')}</th>
                <th>{t('users.table.createdAt')}</th>
                <th>{t('users.table.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {usersData.users.map((user: User) => (
                <tr key={user.id}>
                  <td>
                    <strong>{user.username}</strong>
                    {user.id === currentUser?.id && (
                      <span className="badge badge-primary">{t('users.you')}</span>
                    )}
                  </td>
                  <td>{user.email}</td>
                  <td>
                    <span className={`badge badge-${user.role}`}>
                      {user.role === 'admin' ? t('users.role.admin') : t('users.role.user')}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? t('status.active') : t('status.inactive')}
                    </span>
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="action-buttons">
                      {!user.is_active ? (
                        <button
                          className="btn-icon btn-success"
                          onClick={() => handleApprove(user)}
                          title={t('action.approve')}
                        >
                          ✅
                        </button>
                      ) : (
                        <button
                          className="btn-icon"
                          onClick={() => handleDeactivate(user)}
                          disabled={user.id === currentUser?.id}
                          title={t('action.deactivate')}
                        >
                          ⏸️
                        </button>
                      )}
                      <button
                        className="btn-icon btn-danger"
                        onClick={() => handleDelete(user)}
                        disabled={user.id === currentUser?.id}
                        title={t('action.delete')}
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  )
}
