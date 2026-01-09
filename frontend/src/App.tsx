import { useState, useCallback } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/hooks/useTheme'
import { Dashboard } from '@/components/dashboard/Dashboard'
import { LoginForm } from '@/components/dashboard/LoginForm'
import { getAccessToken } from '@/api/client'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      retry: (failureCount, error) => {
        // Don't retry on 401 errors
        if ((error as { response?: { status?: number } })?.response?.status === 401) {
          return false
        }
        return failureCount < 3
      },
    },
  },
})

// Default site name - can be configured via env
const SITE_NAME = import.meta.env.VITE_SITE_NAME || import.meta.env.VITE_SITE_ID || 'home'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAccessToken())

  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true)
    // Clear any cached queries to refetch with new auth
    queryClient.clear()
  }, [])

  const handleAuthError = useCallback(() => {
    setIsAuthenticated(false)
  }, [])

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        {isAuthenticated ? (
          <Dashboard siteName={SITE_NAME} onAuthError={handleAuthError} />
        ) : (
          <LoginForm onSuccess={handleLoginSuccess} />
        )}
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
