import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-gray-400">
        Restoring your session...
      </main>
    )
  }

  return user ? children : <Navigate to="/login" replace />
}
