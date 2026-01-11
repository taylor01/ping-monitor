import { useState, useCallback } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/hooks/useTheme'
import { SiteOverview } from '@/components/dashboard/SiteOverview'
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

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAccessToken())
  const [selectedSite, setSelectedSite] = useState<string | null>(null)

  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true)
    // Clear any cached queries to refetch with new auth
    queryClient.clear()
  }, [])

  const handleAuthError = useCallback(() => {
    setIsAuthenticated(false)
    setSelectedSite(null)
  }, [])

  const handleSiteSelect = useCallback((siteName: string) => {
    setSelectedSite(siteName)
  }, [])

  const handleBackToOverview = useCallback(() => {
    setSelectedSite(null)
  }, [])

  if (!isAuthenticated) {
    return (
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <LoginForm onSuccess={handleLoginSuccess} />
        </QueryClientProvider>
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        {selectedSite ? (
          <Dashboard
            siteName={selectedSite}
            onAuthError={handleAuthError}
            onBack={handleBackToOverview}
          />
        ) : (
          <SiteOverview
            onSiteSelect={handleSiteSelect}
            onAuthError={handleAuthError}
          />
        )}
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
