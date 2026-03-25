import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi, User } from '../services/api'

// Storage helper to handle both localStorage and sessionStorage
const storage = {
  get: (key: string): string | null => {
    return localStorage.getItem(key) || sessionStorage.getItem(key)
  },
  set: (key: string, value: string, persistent: boolean) => {
    if (persistent) {
      localStorage.setItem(key, value)
      sessionStorage.removeItem(key)
    } else {
      sessionStorage.setItem(key, value)
      localStorage.removeItem(key)
    }
  },
  remove: (key: string) => {
    localStorage.removeItem(key)
    sessionStorage.removeItem(key)
  },
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isGuest: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName: string) => Promise<void>
  loginAsGuest: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isGuest, setIsGuest] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = storage.get('access_token')
      
      if (token) {
        try {
          const status = await authApi.getAuthStatus()
          if (status.authenticated) {
            if (status.user_type === 'guest') {
              setIsGuest(true)
            } else {
              const userData = await authApi.getCurrentUser()
              setUser(userData)
            }
          }
        } catch {
          // Token invalid and refresh failed - clear storage
          storage.remove('access_token')
          storage.remove('refresh_token')
        }
      }
      setIsLoading(false)
    }

    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    const tokens = await authApi.login(email, password)

    storage.set('access_token', tokens.access_token, false)
    if (tokens.refresh_token) {
      storage.set('refresh_token', tokens.refresh_token, false)
    }
    
    const userData = await authApi.getCurrentUser()
    setUser(userData)
    setIsGuest(false)
  }

  const register = async (email: string, password: string, displayName: string) => {
    const tokens = await authApi.register(email, password, displayName)
    storage.set('access_token', tokens.access_token, false)
    if (tokens.refresh_token) {
      storage.set('refresh_token', tokens.refresh_token, false)
    }
    
    const userData = await authApi.getCurrentUser()
    setUser(userData)
    setIsGuest(false)
  }

  const loginAsGuest = async () => {
    const session = await authApi.createGuestSession()
    // Guest sessions are always session-only (not persistent)
    storage.set('access_token', session.access_token, false)
    storage.set('session_id', session.session_id, false)
    setIsGuest(true)
    setUser(null)
  }

  const logout = () => {
    storage.remove('access_token')
    storage.remove('refresh_token')
    storage.remove('session_id')
    setUser(null)
    setIsGuest(false)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user || isGuest,
        isGuest,
        isLoading,
        login,
        register,
        loginAsGuest,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
