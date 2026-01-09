import { useEffect, useState } from 'react'
import { Activity, RefreshCw, LogOut } from 'lucide-react'
import { useSiteByName } from '@/hooks/useSites'
import { useSiteStatus } from '@/hooks/useSiteStatus'
import { useAnomalies, useResolveAnomaly } from '@/hooks/useAnomalies'
import { StatusOverview } from './StatusOverview'
import { DeviceTable } from './DeviceTable'
import { DeviceDetailPanel } from './DeviceDetailPanel'
import { AnomaliesPanel } from './AnomaliesPanel'
import { ThemeToggle } from './ThemeToggle'
import { logout } from '@/api/auth'
import { cn } from '@/lib/utils'
import type { DeviceStatus } from '@/types/api'

interface DashboardProps {
  siteName: string
  onAuthError?: () => void
}

export function Dashboard({ siteName, onAuthError }: DashboardProps) {
  const [selectedDevice, setSelectedDevice] = useState<DeviceStatus | null>(null)

  // First resolve the site name to a numeric ID
  const {
    site,
    isLoading: sitesLoading,
    error: sitesError
  } = useSiteByName(siteName)

  const {
    data: siteStatus,
    isLoading: statusLoading,
    isRefetching: statusRefetching,
    error: statusError,
    refetch: refetchStatus
  } = useSiteStatus(site?.id || '')

  const {
    data: anomalies,
    isLoading: anomaliesLoading,
    isRefetching: anomaliesRefetching
  } = useAnomalies({ status: 'active' })

  const resolveAnomaly = useResolveAnomaly()

  // Handle 401 errors by calling onAuthError
  useEffect(() => {
    const error = sitesError || statusError
    const is401 = (error as { response?: { status?: number } })?.response?.status === 401
    if (is401 && onAuthError) {
      onAuthError()
    }
  }, [sitesError, statusError, onAuthError])

  const handleResolve = (id: string) => {
    resolveAnomaly.mutate(id)
  }

  const isRefetching = statusRefetching || anomaliesRefetching
  const isLoading = sitesLoading || (site && statusLoading)

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--color-void)] grid-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-[var(--color-border)] rounded-full" />
            <div className="absolute inset-0 w-16 h-16 border-4 border-t-[var(--color-cyan)] rounded-full animate-spin" />
          </div>
          <div className="font-[var(--font-display)] text-[var(--color-text-secondary)] uppercase tracking-widest">
            Initializing...
          </div>
        </div>
      </div>
    )
  }

  // Site not found
  if (!sitesLoading && !site) {
    return (
      <div className="min-h-screen bg-[var(--color-void)] grid-bg flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <div className="p-4 rounded-full bg-[var(--color-amber)]/10 inline-block mb-4">
            <Activity size={32} className="text-[var(--color-amber)]" />
          </div>
          <h2 className="font-[var(--font-display)] text-xl text-[var(--color-text-primary)] mb-2 uppercase tracking-wide">
            Site Not Found
          </h2>
          <p className="text-[var(--color-text-secondary)] text-sm mb-4 font-[var(--font-mono)]">
            The site "{siteName}" was not found or you don't have access to it.
          </p>
        </div>
      </div>
    )
  }

  if (sitesError || statusError || !siteStatus) {
    return (
      <div className="min-h-screen bg-[var(--color-void)] grid-bg flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <div className="p-4 rounded-full bg-[var(--color-alert)]/10 inline-block mb-4">
            <Activity size={32} className="text-[var(--color-alert)]" />
          </div>
          <h2 className="font-[var(--font-display)] text-xl text-[var(--color-text-primary)] mb-2 uppercase tracking-wide">
            Connection Error
          </h2>
          <p className="text-[var(--color-text-secondary)] text-sm mb-4 font-[var(--font-mono)]">
            Unable to connect to monitoring API. Please check your connection and try again.
          </p>
          <button
            onClick={() => refetchStatus()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[var(--color-cyan)]/10 border border-[var(--color-cyan)]/30 text-[var(--color-cyan)] font-[var(--font-display)] uppercase tracking-wider text-sm hover:bg-[var(--color-cyan)]/20 transition-colors"
          >
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--color-void)] grid-bg">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[var(--color-panel)]/80 backdrop-blur-md border-b border-[var(--color-border)]">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-[var(--color-cyan)]/10 border border-[var(--color-cyan)]/30">
                <Activity size={20} className="text-[var(--color-cyan)]" />
              </div>
              <div>
                <h1 className="font-[var(--font-display)] text-lg font-bold text-[var(--color-text-primary)] uppercase tracking-wider">
                  NetMon
                </h1>
                <p className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)]">
                  Network Operations Center
                </p>
              </div>
            </div>
          </div>

          {/* Status & Controls */}
          <div className="flex items-center gap-3">
            {/* Refresh indicator */}
            <div className={cn(
              'flex items-center gap-2 text-xs font-[var(--font-mono)] transition-opacity',
              isRefetching ? 'opacity-100' : 'opacity-0'
            )}>
              <RefreshCw size={14} className="text-[var(--color-cyan)] animate-spin" />
              <span className="text-[var(--color-text-muted)]">Syncing...</span>
            </div>

            {/* Live indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--color-terminal)]/10 border border-[var(--color-terminal)]/30">
              <div className="w-2 h-2 rounded-full bg-[var(--color-terminal)] pulse-terminal" />
              <span className="text-xs font-[var(--font-mono)] text-[var(--color-terminal)] uppercase tracking-wider">
                Live
              </span>
            </div>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Logout Button */}
            <button
              onClick={() => {
                logout()
                onAuthError?.()
              }}
              className={cn(
                'flex items-center justify-center w-10 h-10 rounded-lg transition-all',
                'border border-[var(--color-border)] hover:border-[var(--color-alert)]/50',
                'bg-[var(--color-surface)] hover:bg-[var(--color-alert)]/10',
                'text-[var(--color-text-secondary)] hover:text-[var(--color-alert)]'
              )}
              title="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1800px] mx-auto px-6 py-6">
        <div className="flex flex-col xl:flex-row gap-6">
          {/* Left Column - Main content */}
          <div className="flex-1 space-y-6">
            <StatusOverview status={siteStatus} isRefetching={statusRefetching} />
            <DeviceTable devices={siteStatus.devices} onDeviceClick={setSelectedDevice} />
          </div>

          {/* Right Column - Alerts sidebar */}
          <div className="xl:w-[380px] xl:flex-shrink-0">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-4">
              <AnomaliesPanel
                anomalies={anomalies || []}
                onResolve={handleResolve}
                isLoading={anomaliesLoading}
                maxHeight={520}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] bg-[var(--color-panel)]/50 mt-auto">
        <div className="max-w-[1800px] mx-auto px-6 py-3 flex items-center justify-between text-xs font-[var(--font-mono)] text-[var(--color-text-muted)]">
          <span>Network Monitoring Dashboard v1.0</span>
          <span>Auto-refresh: 10s</span>
        </div>
      </footer>

      {/* Device Detail Modal */}
      {selectedDevice && (
        <DeviceDetailPanel
          device={selectedDevice}
          onClose={() => setSelectedDevice(null)}
        />
      )}
    </div>
  )
}
