import { AppProps } from 'next/app'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import '../styles/globals.css'

// Authentication Context
interface AuthContextType {
  apiKey: string | null
  isAuthenticated: boolean
  login: (key: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

const AuthProvider = ({ children }: AuthProviderProps) => {
  const [apiKey, setApiKey] = useState<string | null>(null)

  useEffect(() => {
    // Load API key from localStorage on mount
    const savedKey = localStorage.getItem('audiobook-api-key')
    if (savedKey) {
      setApiKey(savedKey)
    }
  }, [])

  const login = (key: string) => {
    setApiKey(key)
    localStorage.setItem('audiobook-api-key', key)
  }

  const logout = () => {
    setApiKey(null)
    localStorage.removeItem('audiobook-api-key')
  }

  const value = {
    apiKey,
    isAuthenticated: !!apiKey,
    login,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export default function App({ Component, pageProps }: AppProps) {
  return (
    <AuthProvider>
      <Component {...pageProps} />
    </AuthProvider>
  )
} 