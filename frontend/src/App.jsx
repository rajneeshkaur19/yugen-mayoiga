import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LandingPage from './pages/Landing/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import CreateStoryPage from './pages/CreateStoryPage'
import StoryReaderPage from './pages/StoryReaderPage'
import ProtectedRoute from './components/ProtectedRoute'

function RootRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#101317] text-sm text-[#858A8D]">
        <div className="flex items-center gap-3">
          <div className="h-2 w-2 rounded-full bg-[#A33B42] animate-ping" />
          <span>Entering the sanctuary...</span>
        </div>
      </main>
    )
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return <LandingPage />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRoute />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/stories/new" element={<ProtectedRoute><CreateStoryPage /></ProtectedRoute>} />
      <Route path="/stories/:storyId" element={<ProtectedRoute><StoryReaderPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
