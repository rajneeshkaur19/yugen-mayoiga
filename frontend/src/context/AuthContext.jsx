import { createContext, useContext, useEffect, useState } from 'react'
import { authApi, clearToken, getToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function restoreSession() {
      if (!getToken()) {
        setLoading(false)
        return
      }

      try {
        const currentUser = await authApi.me()
        if (active) setUser(currentUser)
      } catch {
        clearToken()
        if (active) setUser(null)
      } finally {
        if (active) setLoading(false)
      }
    }

    restoreSession()

    function handleUnauthorized() {
      clearToken()
      if (active) setUser(null)
    }
    window.addEventListener('yugen:unauthorized', handleUnauthorized)

    return () => {
      active = false
      window.removeEventListener('yugen:unauthorized', handleUnauthorized)
    }
  }, [])

  async function login(credentials) {
    await authApi.login(credentials)
    const currentUser = await authApi.me()
    setUser(currentUser)
    return currentUser
  }

  async function register(userData) {
    return authApi.register(userData)
  }

  function logout() {
    authApi.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}
