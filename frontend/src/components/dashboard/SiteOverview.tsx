import { Activity, Server, AlertTriangle, CheckCircle2, XCircle, RefreshCw, LogOut, ChevronRight } from 'lucide-react'
import { useSites } from '@/hooks/useSites'
import { useAllSiteStatuses } from '@/hooks/useAllSiteStatuses'
import { useAnomalies } from '@/hooks/useAnomalies'
import { ThemeToggle } from './ThemeToggle'
import { logout } from '@/api/auth'
import { cn } from '@/lib/utils'
import type { SiteStatus } from '@/types/api'

interface SiteOverviewProps {
  onSiteSelect: (siteName: string) => void
  onAuthError?: () => void
}

function getStatusColor(status: SiteStatus['status'] | undefined) {
  switch (status) {
    case 'healthy':
      return {
        bg: 'bg-[var(--color-terminal)]/10',
        border: 'border-[var(--color-terminal)]/40',
        text: 'text-[var(--color-terminal)]',
        glow: 'glow-terminal',
        pulse: 'pulse-terminal',
        icon: CheckCircle2,
      }
    case 'degraded':
      return {
        bg: 'bg-[var(--color-amber)]/10',
        border: 'border-[var(--color-amber)]/40',
        text: 'text-[var(--color-amber)]',
        glow: 'glow-amber',
        pulse: 'pulse-amber',
        icon: AlertTriangle,
      }
    case 'critical':
    case 'offline':
      return {
        bg: 'bg-[var(--color-alert)]/10',
        border: 'border-[var(--color-alert)]/40',
        text: 'text-[var(--color-alert)]',
        glow: 'glow-alert',
        pulse: 'pulse-alert',
        icon: XCircle,
      }
    default:
      return {
        bg: 'bg-[var(--color-surface)]',
        border: 'border-[var(--color-border)]',
        text: 'text-[var(--color-text-secondary)]',
        glow: '',
        pulse: '',
        icon: Server,
      }
  }
}

function formatLastSeen(dateStr: string | null): string {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60) return 'Just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

export function SiteOverview({ onSiteSelect, onAuthError }: SiteOverviewProps) {
  const { data: sites, isLoading: sitesLoading, error: sitesError } = useSites()
  const { sites: sitesWithStatus, isLoading: statusLoading, isRefetching } = useAllSiteStatuses(sites)
  const { data: anomalies } = useAnomalies({ status: 'active' })

  // Count anomalies per site
  const anomaliesBySite = (anomalies || []).reduce((acc, anomaly) => {
    // Extract site from the anomaly (this might need adjustment based on actual data structure)
    const siteName = (anomaly as unknown as { site?: { name?: string } })?.site?.name || 'unknown'
    acc[siteName] = (acc[siteName] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const isLoading = sitesLoading || (sites && sites.length > 0 && statusLoading)

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--color-void)] grid-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-[var(--color-border)] rounded-full" />
            <div className="absolute inset-0 w-16 h-16 border-4 border-t-[var(--color-cyan)] rounded-full animate-spin" />
          </div>
          <div className="font-[var(--font-display)] text-[var(--color-text-secondary)] uppercase tracking-widest">
            Loading Sites...
          </div>
        </div>
      </div>
    )
  }

  if (sitesError) {
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
            Unable to load sites. Please check your connection.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--color-void)] grid-bg">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[var(--color-panel)]/80 backdrop-blur-md border-b border-[var(--color-border)]">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-[var(--color-cyan)]/10 border border-[var(--color-cyan)]/30">
                <Activity size={24} className="text-[var(--color-cyan)]" />
              </div>
              <div>
                <h1 className="font-[var(--font-display)] text-xl font-bold text-[var(--color-text-primary)] uppercase tracking-wider">
                  NetMon
                </h1>
                <p className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)]">
                  Network Operations Center
                </p>
              </div>
            </div>
          </div>

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

            <ThemeToggle />

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
      <main className="max-w-[1400px] mx-auto px-6 py-8">
        {/* Section Header */}
        <div className="mb-8">
          <h2 className="font-[var(--font-display)] text-2xl font-bold text-[var(--color-text-primary)] uppercase tracking-wide mb-2">
            Monitored Sites
          </h2>
          <p className="font-[var(--font-mono)] text-sm text-[var(--color-text-secondary)]">
            Select a site to view detailed network status and device information
          </p>
        </div>

        {/* Site Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sitesWithStatus.map((site, index) => {
            const statusConfig = getStatusColor(site.siteStatus?.status)
            const StatusIcon = statusConfig.icon
            const siteAnomalies = anomaliesBySite[site.name] || 0

            return (
              <button
                key={site.id}
                onClick={() => onSiteSelect(site.name)}
                className={cn(
                  'group relative text-left rounded-xl border-2 p-6 transition-all duration-300',
                  'bg-[var(--color-panel)] hover:bg-[var(--color-surface)]',
                  statusConfig.border,
                  'hover:scale-[1.02] hover:-translate-y-1',
                  'animate-fade-in-up',
                  site.siteStatus?.status === 'healthy' && 'hover:glow-terminal',
                  site.siteStatus?.status === 'degraded' && 'hover:glow-amber',
                  (site.siteStatus?.status === 'critical' || site.siteStatus?.status === 'offline') && 'hover:glow-alert'
                )}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* Status Indicator Bar */}
                <div className={cn(
                  'absolute top-0 left-6 right-6 h-1 rounded-b-full',
                  statusConfig.bg.replace('/10', '/60')
                )} />

                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'p-3 rounded-lg',
                      statusConfig.bg,
                      'border',
                      statusConfig.border
                    )}>
                      <Server size={24} className={statusConfig.text} />
                    </div>
                    <div>
                      <h3 className="font-[var(--font-display)] text-xl font-bold text-[var(--color-text-primary)] uppercase tracking-wide">
                        {site.name}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusIcon size={14} className={statusConfig.text} />
                        <span className={cn('font-[var(--font-mono)] text-xs uppercase tracking-wider', statusConfig.text)}>
                          {site.siteStatus?.status || 'Loading...'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Status Dot */}
                  <div className={cn(
                    'w-3 h-3 rounded-full',
                    statusConfig.bg.replace('/10', ''),
                    statusConfig.pulse
                  )} />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="text-center p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <div className="font-[var(--font-mono)] text-2xl font-bold text-[var(--color-text-primary)]">
                      {site.siteStatus?.devicesTotal ?? '-'}
                    </div>
                    <div className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
                      Devices
                    </div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <div className={cn(
                      'font-[var(--font-mono)] text-2xl font-bold',
                      site.siteStatus?.devicesUp === site.siteStatus?.devicesTotal
                        ? 'text-[var(--color-terminal)]'
                        : 'text-[var(--color-text-primary)]'
                    )}>
                      {site.siteStatus?.devicesUp ?? '-'}
                    </div>
                    <div className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
                      Online
                    </div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <div className={cn(
                      'font-[var(--font-mono)] text-2xl font-bold',
                      siteAnomalies > 0 ? 'text-[var(--color-amber)]' : 'text-[var(--color-text-primary)]'
                    )}>
                      {siteAnomalies}
                    </div>
                    <div className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
                      Alerts
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-4 border-t border-[var(--color-border)]">
                  <div className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)]">
                    Last data: {formatLastSeen(site.siteStatus?.lastDataAt ?? null)}
                  </div>
                  <div className={cn(
                    'flex items-center gap-1 font-[var(--font-display)] text-sm uppercase tracking-wider',
                    'text-[var(--color-text-secondary)] group-hover:text-[var(--color-cyan)]',
                    'transition-colors'
                  )}>
                    View Details
                    <ChevronRight size={16} className="transition-transform group-hover:translate-x-1" />
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Empty State */}
        {sitesWithStatus.length === 0 && !isLoading && (
          <div className="text-center py-16">
            <div className="p-4 rounded-full bg-[var(--color-surface)] inline-block mb-4">
              <Server size={32} className="text-[var(--color-text-muted)]" />
            </div>
            <h3 className="font-[var(--font-display)] text-lg text-[var(--color-text-primary)] uppercase tracking-wide mb-2">
              No Sites Found
            </h3>
            <p className="font-[var(--font-mono)] text-sm text-[var(--color-text-secondary)]">
              No monitored sites are configured yet.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] bg-[var(--color-panel)]/50 mt-auto">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between text-xs font-[var(--font-mono)] text-[var(--color-text-muted)]">
          <span>Network Monitoring Dashboard v1.0</span>
          <span>Auto-refresh: 15s</span>
        </div>
      </footer>
    </div>
  )
}
