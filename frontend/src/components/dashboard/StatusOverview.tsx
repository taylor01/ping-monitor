import { Activity, AlertTriangle, Server, ServerOff } from 'lucide-react'
import type { SiteStatus } from '@/types/api'
import { cn } from '@/lib/utils'

interface StatusOverviewProps {
  status: SiteStatus
  isRefetching?: boolean
}

interface StatCardProps {
  label: string
  value: number | string
  icon: React.ReactNode
  variant: 'healthy' | 'warning' | 'critical' | 'info'
  subtext?: string
  delay?: number
}

function StatCard({ label, value, icon, variant, subtext, delay = 0 }: StatCardProps) {
  const variantStyles = {
    healthy: {
      border: 'border-[var(--color-terminal)]/30',
      glow: 'glow-terminal',
      text: 'text-[var(--color-terminal)]',
      bg: 'bg-[var(--color-terminal)]/5',
    },
    warning: {
      border: 'border-[var(--color-amber)]/30',
      glow: 'glow-amber',
      text: 'text-[var(--color-amber)]',
      bg: 'bg-[var(--color-amber)]/5',
    },
    critical: {
      border: 'border-[var(--color-alert)]/30',
      glow: 'glow-alert',
      text: 'text-[var(--color-alert)]',
      bg: 'bg-[var(--color-alert)]/5',
    },
    info: {
      border: 'border-[var(--color-cyan)]/30',
      glow: 'glow-cyan',
      text: 'text-[var(--color-cyan)]',
      bg: 'bg-[var(--color-cyan)]/5',
    },
  }

  const styles = variantStyles[variant]

  return (
    <div
      className={cn(
        'animate-fade-in-up relative overflow-hidden rounded-lg border bg-[var(--color-panel)] p-5',
        styles.border,
        variant !== 'info' && styles.glow
      )}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Corner accent */}
      <div className={cn('absolute top-0 right-0 w-16 h-16 -mr-8 -mt-8 rounded-full opacity-20', styles.bg)} />

      {/* Top row: icon and label */}
      <div className="flex items-center gap-3 mb-3">
        <div className={cn('p-2 rounded-md', styles.bg)}>
          <span className={styles.text}>{icon}</span>
        </div>
        <span className="text-[var(--color-text-secondary)] font-medium text-sm uppercase tracking-wider font-[var(--font-display)]">
          {label}
        </span>
      </div>

      {/* Value */}
      <div className={cn('font-[var(--font-mono)] text-4xl font-bold tracking-tight', styles.text)}>
        {value}
      </div>

      {/* Subtext */}
      {subtext && (
        <div className="mt-2 text-[var(--color-text-muted)] text-xs font-[var(--font-mono)]">
          {subtext}
        </div>
      )}

      {/* Bottom accent line */}
      <div className={cn('absolute bottom-0 left-0 right-0 h-0.5 opacity-50', styles.bg.replace('/5', ''))} />
    </div>
  )
}

export function StatusOverview({ status, isRefetching }: StatusOverviewProps) {
  const uptimePercent = status.devicesTotal > 0
    ? ((status.devicesUp / status.devicesTotal) * 100).toFixed(1)
    : '0.0'

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-[var(--font-display)] text-xl font-semibold text-[var(--color-text-primary)] uppercase tracking-wide">
          System Overview
        </h2>
        {isRefetching && (
          <div className="flex items-center gap-2 text-[var(--color-cyan)] text-xs font-[var(--font-mono)]">
            <div className="w-2 h-2 rounded-full bg-[var(--color-cyan)] data-updating" />
            SYNCING
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Online"
          value={status.devicesUp}
          icon={<Server size={20} />}
          variant="healthy"
          subtext={`${uptimePercent}% uptime`}
          delay={0}
        />
        <StatCard
          label="Offline"
          value={status.devicesDown}
          icon={<ServerOff size={20} />}
          variant={status.devicesDown > 0 ? 'critical' : 'info'}
          subtext={status.devicesDown > 0 ? 'Requires attention' : 'All systems nominal'}
          delay={50}
        />
        <StatCard
          label="Anomalies"
          value={status.activeAnomalies}
          icon={<AlertTriangle size={20} />}
          variant={status.activeAnomalies > 0 ? 'warning' : 'info'}
          subtext={status.activeAnomalies > 0 ? 'Active alerts' : 'No active alerts'}
          delay={100}
        />
        <StatCard
          label="Total Devices"
          value={status.devicesTotal}
          icon={<Activity size={20} />}
          variant="info"
          subtext="Monitored endpoints"
          delay={150}
        />
      </div>

      {/* Status Banner */}
      <div
        className={cn(
          'animate-fade-in-up rounded-lg border px-4 py-3 font-[var(--font-mono)] text-sm flex items-center gap-3',
          status.status === 'healthy' && 'border-[var(--color-terminal)]/30 bg-[var(--color-terminal)]/5 text-[var(--color-terminal)]',
          status.status === 'degraded' && 'border-[var(--color-amber)]/30 bg-[var(--color-amber)]/5 text-[var(--color-amber)]',
          status.status === 'critical' && 'border-[var(--color-alert)]/30 bg-[var(--color-alert)]/5 text-[var(--color-alert)]',
          status.status === 'offline' && 'border-[var(--color-alert)]/30 bg-[var(--color-alert)]/5 text-[var(--color-alert)]'
        )}
        style={{ animationDelay: '200ms' }}
      >
        <div
          className={cn(
            'w-3 h-3 rounded-full',
            status.status === 'healthy' && 'bg-[var(--color-terminal)] pulse-terminal',
            status.status === 'degraded' && 'bg-[var(--color-amber)] pulse-amber',
            status.status === 'critical' && 'bg-[var(--color-alert)] pulse-alert',
            status.status === 'offline' && 'bg-[var(--color-alert)] pulse-alert'
          )}
        />
        <span className="uppercase tracking-wider">
          System Status: {status.status}
        </span>
        <span className="text-[var(--color-text-muted)] ml-auto">
          {status.name}
        </span>
      </div>
    </div>
  )
}
