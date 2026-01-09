import { AlertTriangle, AlertCircle, Info, Clock, CheckCircle2, X } from 'lucide-react'
import type { Anomaly, AnomalySeverity, AnomalyType } from '@/types/api'
import { cn, formatRelativeTime } from '@/lib/utils'

interface AnomaliesPanelProps {
  anomalies: Anomaly[]
  onResolve?: (id: string) => void
  isLoading?: boolean
}

const severityConfig: Record<AnomalySeverity, { icon: React.ReactNode; color: string; bg: string; border: string }> = {
  critical: {
    icon: <AlertCircle size={16} />,
    color: 'text-[var(--color-alert)]',
    bg: 'bg-[var(--color-alert)]/10',
    border: 'border-[var(--color-alert)]/30',
  },
  warning: {
    icon: <AlertTriangle size={16} />,
    color: 'text-[var(--color-amber)]',
    bg: 'bg-[var(--color-amber)]/10',
    border: 'border-[var(--color-amber)]/30',
  },
  info: {
    icon: <Info size={16} />,
    color: 'text-[var(--color-cyan)]',
    bg: 'bg-[var(--color-cyan)]/10',
    border: 'border-[var(--color-cyan)]/30',
  },
}

const anomalyTypeLabels: Record<AnomalyType, string> = {
  host_down: 'Host Down',
  host_recovery: 'Host Recovered',
  latency_spike: 'High Latency',
  packet_loss: 'Packet Loss',
  site_offline: 'Site Offline',
}

function AnomalyCard({ anomaly, onResolve, index }: { anomaly: Anomaly; onResolve?: (id: string) => void; index: number }) {
  const config = severityConfig[anomaly.severity]

  return (
    <div
      className={cn(
        'animate-fade-in-up relative rounded-lg border p-4 transition-all hover:scale-[1.01]',
        config.border,
        config.bg
      )}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className={config.color}>{config.icon}</span>
          <span className={cn('text-xs uppercase tracking-wider font-[var(--font-display)] font-semibold', config.color)}>
            {anomaly.severity}
          </span>
        </div>
        {onResolve && anomaly.active && (
          <button
            onClick={() => onResolve(anomaly.id)}
            className="p-1 rounded hover:bg-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
            title="Resolve"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Host */}
      <div className="font-[var(--font-mono)] text-sm text-[var(--color-text-primary)] mb-1">
        {anomaly.host}
      </div>

      {/* Type Badge */}
      <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-[var(--font-mono)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] mb-2">
        {anomalyTypeLabels[anomaly.anomalyType] || anomaly.anomalyType}
      </div>

      {/* Message */}
      <p className="text-xs text-[var(--color-text-secondary)] mb-3 line-clamp-2">
        {anomaly.message}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
        <div className="flex items-center gap-1 font-[var(--font-mono)]">
          <Clock size={12} />
          {formatRelativeTime(anomaly.createdAt)}
        </div>
        {anomaly.duration && (
          <span className="font-[var(--font-mono)]">
            Duration: {anomaly.duration}
          </span>
        )}
      </div>

      {/* Accent bar */}
      <div className={cn('absolute left-0 top-0 bottom-0 w-1 rounded-l-lg', config.bg.replace('/10', ''))} />
    </div>
  )
}

export function AnomaliesPanel({ anomalies, onResolve, isLoading }: AnomaliesPanelProps) {
  const criticalCount = anomalies.filter(a => a.severity === 'critical').length
  const warningCount = anomalies.filter(a => a.severity === 'warning').length

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="font-[var(--font-display)] text-xl font-semibold text-[var(--color-text-primary)] uppercase tracking-wide">
            Alerts
          </h2>
          {anomalies.length > 0 && (
            <div className="flex items-center gap-2">
              {criticalCount > 0 && (
                <span className="px-2 py-0.5 rounded text-xs font-[var(--font-mono)] font-semibold bg-[var(--color-alert)]/20 text-[var(--color-alert)]">
                  {criticalCount} critical
                </span>
              )}
              {warningCount > 0 && (
                <span className="px-2 py-0.5 rounded text-xs font-[var(--font-mono)] font-semibold bg-[var(--color-amber)]/20 text-[var(--color-amber)]">
                  {warningCount} warning
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-[var(--color-text-muted)]">
            <div className="w-5 h-5 border-2 border-[var(--color-cyan)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : anomalies.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-3 rounded-full bg-[var(--color-terminal)]/10 mb-3">
              <CheckCircle2 size={24} className="text-[var(--color-terminal)]" />
            </div>
            <p className="text-[var(--color-text-secondary)] font-[var(--font-display)] font-medium">
              All Clear
            </p>
            <p className="text-xs text-[var(--color-text-muted)] font-[var(--font-mono)]">
              No active alerts
            </p>
          </div>
        ) : (
          anomalies.map((anomaly, index) => (
            <AnomalyCard
              key={anomaly.id}
              anomaly={anomaly}
              onResolve={onResolve}
              index={index}
            />
          ))
        )}
      </div>

      {/* Footer */}
      {anomalies.length > 0 && (
        <div className="flex-shrink-0 mt-4 pt-3 border-t border-[var(--color-border)] text-xs text-[var(--color-text-muted)] font-[var(--font-mono)]">
          {anomalies.length} active alert{anomalies.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}
