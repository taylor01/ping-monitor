import { X, Activity, Clock, Wifi, AlertTriangle } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'
import type { DeviceStatus } from '@/types/api'
import { useDeviceMeasurements } from '@/hooks/useMeasurements'
import { cn, formatLatency, formatPacketLoss } from '@/lib/utils'

interface DeviceDetailPanelProps {
  device: DeviceStatus
  onClose: () => void
}

function getStatusVariant(device: DeviceStatus): 'online' | 'warning' | 'offline' {
  if (!device.isUp) return 'offline'
  if (device.latencyMs && device.latencyMs > 100) return 'warning'
  if (device.packetLoss && device.packetLoss > 0.05) return 'warning'
  return 'online'
}

export function DeviceDetailPanel({ device, onClose }: DeviceDetailPanelProps) {
  const { data: measurements, isLoading } = useDeviceMeasurements({
    host: device.host,
    since: 60, // Last hour
  })

  const status = getStatusVariant(device)

  // Prepare chart data - reverse to show oldest first
  const chartData = measurements
    ?.slice()
    .reverse()
    .map((m) => ({
      time: new Date(m.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
      latency: m.latencyMs,
      packetLoss: m.packetLoss ? m.packetLoss * 100 : 0,
      isUp: m.isUp,
    })) || []

  // Calculate stats
  const latencies = measurements?.filter(m => m.latencyMs !== null).map(m => m.latencyMs!) || []
  const avgLatency = latencies.length > 0
    ? latencies.reduce((a, b) => a + b, 0) / latencies.length
    : null
  const maxLatency = latencies.length > 0 ? Math.max(...latencies) : null
  const minLatency = latencies.length > 0 ? Math.min(...latencies) : null
  const downCount = measurements?.filter(m => !m.isUp).length || 0
  const uptime = measurements?.length
    ? ((measurements.length - downCount) / measurements.length) * 100
    : 100

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] shadow-2xl animate-fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-[var(--color-border)] bg-[var(--color-panel)]">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'w-3 h-3 rounded-full',
                status === 'online' && 'bg-[var(--color-terminal)] pulse-terminal',
                status === 'warning' && 'bg-[var(--color-amber)] pulse-amber',
                status === 'offline' && 'bg-[var(--color-alert)] pulse-alert'
              )}
            />
            <div>
              <h2 className="font-[var(--font-display)] text-lg font-semibold text-[var(--color-text-primary)] uppercase tracking-wide">
                {device.host}
              </h2>
              <p className="font-[var(--font-mono)] text-sm text-[var(--color-text-muted)]">
                {device.ip}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-[var(--color-surface)] transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={<Activity size={18} />}
              label="Current Latency"
              value={formatLatency(device.latencyMs)}
              variant={device.latencyMs && device.latencyMs > 100 ? 'warning' : 'default'}
            />
            <StatCard
              icon={<Wifi size={18} />}
              label="Packet Loss"
              value={formatPacketLoss(device.packetLoss)}
              variant={device.packetLoss && device.packetLoss > 0.05 ? 'warning' : 'default'}
            />
            <StatCard
              icon={<Clock size={18} />}
              label="Uptime (1h)"
              value={`${uptime.toFixed(1)}%`}
              variant={uptime < 99 ? 'warning' : 'default'}
            />
            <StatCard
              icon={<AlertTriangle size={18} />}
              label="Outages (1h)"
              value={downCount.toString()}
              variant={downCount > 0 ? 'alert' : 'default'}
            />
          </div>

          {/* Latency Chart */}
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <h3 className="font-[var(--font-display)] text-sm font-semibold text-[var(--color-text-primary)] uppercase tracking-wide mb-4">
              Latency (Last Hour)
            </h3>
            {isLoading ? (
              <div className="h-48 flex items-center justify-center text-[var(--color-text-muted)]">
                Loading...
              </div>
            ) : chartData.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-[var(--color-text-muted)] font-[var(--font-mono)]">
                No data available
              </div>
            ) : (
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      dataKey="time"
                      stroke="var(--color-text-muted)"
                      fontSize={10}
                      tickLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      stroke="var(--color-text-muted)"
                      fontSize={10}
                      tickLine={false}
                      tickFormatter={(v) => `${v}ms`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--color-panel)',
                        border: '1px solid var(--color-border)',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontFamily: 'var(--font-mono)',
                      }}
                      labelStyle={{ color: 'var(--color-text-primary)' }}
                      formatter={(value) => [`${(value as number)?.toFixed(1)}ms`, 'Latency']}
                    />
                    {avgLatency && (
                      <ReferenceLine
                        y={avgLatency}
                        stroke="var(--color-cyan)"
                        strokeDasharray="5 5"
                        strokeOpacity={0.5}
                      />
                    )}
                    <Line
                      type="monotone"
                      dataKey="latency"
                      stroke="var(--color-terminal)"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: 'var(--color-terminal)' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Stats Summary */}
          {latencies.length > 0 && (
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
                <p className="text-xs text-[var(--color-text-muted)] font-[var(--font-display)] uppercase tracking-wider mb-1">
                  Min
                </p>
                <p className="font-[var(--font-mono)] text-lg text-[var(--color-terminal)]">
                  {formatLatency(minLatency)}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
                <p className="text-xs text-[var(--color-text-muted)] font-[var(--font-display)] uppercase tracking-wider mb-1">
                  Avg
                </p>
                <p className="font-[var(--font-mono)] text-lg text-[var(--color-cyan)]">
                  {formatLatency(avgLatency)}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
                <p className="text-xs text-[var(--color-text-muted)] font-[var(--font-display)] uppercase tracking-wider mb-1">
                  Max
                </p>
                <p className={cn(
                  'font-[var(--font-mono)] text-lg',
                  maxLatency && maxLatency > 100 ? 'text-[var(--color-amber)]' : 'text-[var(--color-text-primary)]'
                )}>
                  {formatLatency(maxLatency)}
                </p>
              </div>
            </div>
          )}

          {/* Device Info */}
          {device.description && (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
              <h3 className="font-[var(--font-display)] text-sm font-semibold text-[var(--color-text-primary)] uppercase tracking-wide mb-2">
                Description
              </h3>
              <p className="font-[var(--font-mono)] text-sm text-[var(--color-text-secondary)]">
                {device.description}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  variant = 'default'
}: {
  icon: React.ReactNode
  label: string
  value: string
  variant?: 'default' | 'warning' | 'alert'
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className={cn(
          variant === 'warning' && 'text-[var(--color-amber)]',
          variant === 'alert' && 'text-[var(--color-alert)]',
          variant === 'default' && 'text-[var(--color-text-muted)]'
        )}>
          {icon}
        </span>
        <span className="text-xs text-[var(--color-text-muted)] font-[var(--font-display)] uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p className={cn(
        'font-[var(--font-mono)] text-xl font-semibold',
        variant === 'warning' && 'text-[var(--color-amber)]',
        variant === 'alert' && 'text-[var(--color-alert)]',
        variant === 'default' && 'text-[var(--color-text-primary)]'
      )}>
        {value}
      </p>
    </div>
  )
}
