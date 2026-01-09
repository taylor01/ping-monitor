import { useState } from 'react'
import {
  Router,
  Network,
  Wifi,
  Camera,
  HardDrive,
  Server,
  Link,
  Cpu,
  Shield,
  Tv,
  Zap,
  Monitor,
  Globe,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search
} from 'lucide-react'
import type { DeviceStatus, DeviceType } from '@/types/api'
import { cn, formatLatency, formatPacketLoss, formatRelativeTime } from '@/lib/utils'

interface DeviceTableProps {
  devices: DeviceStatus[]
  onDeviceClick?: (device: DeviceStatus) => void
}

type SortKey = 'host' | 'ip' | 'status' | 'latency' | 'packetLoss'
type SortDir = 'asc' | 'desc'

const ITEMS_PER_PAGE = 10

const deviceIcons: Record<DeviceType, React.ReactNode> = {
  router: <Router size={16} />,
  switch: <Network size={16} />,
  ap: <Wifi size={16} />,
  camera: <Camera size={16} />,
  nas: <HardDrive size={16} />,
  server: <Server size={16} />,
  bridge: <Link size={16} />,
  iot: <Cpu size={16} />,
  safety: <Shield size={16} />,
  media: <Tv size={16} />,
  power: <Zap size={16} />,
  viewport: <Monitor size={16} />,
  external: <Globe size={16} />,
  ups: <Zap size={16} />,
}

function getStatusVariant(device: DeviceStatus): 'online' | 'warning' | 'offline' {
  if (!device.isUp) return 'offline'
  if (device.latencyMs && device.latencyMs > 100) return 'warning'
  if (device.packetLoss && device.packetLoss > 0.05) return 'warning'
  return 'online'
}

function getStatusPriority(device: DeviceStatus): number {
  // Lower number = higher priority (shown first)
  if (!device.isUp) return 0 // Down devices first
  if (device.latencyMs && device.latencyMs > 100) return 1 // Warning
  if (device.packetLoss && device.packetLoss > 0.05) return 1 // Warning
  return 2 // Online/healthy last
}

function StatusIndicator({ status }: { status: 'online' | 'warning' | 'offline' }) {
  return (
    <div
      className={cn(
        'w-2.5 h-2.5 rounded-full',
        status === 'online' && 'bg-[var(--color-terminal)] pulse-terminal',
        status === 'warning' && 'bg-[var(--color-amber)] pulse-amber',
        status === 'offline' && 'bg-[var(--color-alert)] pulse-alert'
      )}
    />
  )
}

function SortButton({
  active,
  direction,
  onClick,
  children
}: {
  active: boolean
  direction: SortDir
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1 text-xs uppercase tracking-wider font-[var(--font-display)] font-semibold transition-colors',
        active ? 'text-[var(--color-cyan)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
      )}
    >
      {children}
      {active && (
        direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
      )}
    </button>
  )
}

export function DeviceTable({ devices, onDeviceClick }: DeviceTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('status')
  const [sortDir, setSortDir] = useState<SortDir>('asc') // asc so down (priority 0) comes first
  const [search, setSearch] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      // Default direction based on column
      setSortDir(key === 'status' ? 'asc' : 'desc')
    }
    setCurrentPage(1) // Reset to first page on sort change
  }

  const filteredDevices = devices.filter(d =>
    d.host.toLowerCase().includes(search.toLowerCase()) ||
    d.ip.includes(search) ||
    d.description?.toLowerCase().includes(search.toLowerCase())
  )

  const sortedDevices = [...filteredDevices].sort((a, b) => {
    const mult = sortDir === 'asc' ? 1 : -1
    switch (sortKey) {
      case 'host':
        return mult * a.host.localeCompare(b.host)
      case 'ip':
        return mult * a.ip.localeCompare(b.ip)
      case 'status':
        // Sort by priority: down first, then warning, then online
        return mult * (getStatusPriority(a) - getStatusPriority(b))
      case 'latency':
        return mult * ((a.latencyMs ?? 999999) - (b.latencyMs ?? 999999))
      case 'packetLoss':
        return mult * ((a.packetLoss ?? 0) - (b.packetLoss ?? 0))
      default:
        return 0
    }
  })

  // Pagination
  const totalPages = Math.ceil(sortedDevices.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const paginatedDevices = sortedDevices.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  const handlePageChange = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  // Reset to page 1 when search changes
  const handleSearchChange = (value: string) => {
    setSearch(value)
    setCurrentPage(1)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-[var(--font-display)] text-xl font-semibold text-[var(--color-text-primary)] uppercase tracking-wide">
          Devices
        </h2>

        {/* Search */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            placeholder="Search devices..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-64 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md py-2 pl-10 pr-4 text-sm font-[var(--font-mono)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-cyan)] focus:ring-1 focus:ring-[var(--color-cyan)]/20 transition-colors"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-[auto_1fr_140px_100px_100px_100px_100px] gap-4 px-4 py-3 bg-[var(--color-surface)] border-b border-[var(--color-border)]">
          <div className="w-6" /> {/* Status indicator */}
          <SortButton active={sortKey === 'host'} direction={sortDir} onClick={() => handleSort('host')}>
            Host
          </SortButton>
          <SortButton active={sortKey === 'ip'} direction={sortDir} onClick={() => handleSort('ip')}>
            IP Address
          </SortButton>
          <div className="text-xs uppercase tracking-wider font-[var(--font-display)] font-semibold text-[var(--color-text-muted)]">
            Type
          </div>
          <SortButton active={sortKey === 'latency'} direction={sortDir} onClick={() => handleSort('latency')}>
            Latency
          </SortButton>
          <SortButton active={sortKey === 'packetLoss'} direction={sortDir} onClick={() => handleSort('packetLoss')}>
            Loss
          </SortButton>
          <div className="text-xs uppercase tracking-wider font-[var(--font-display)] font-semibold text-[var(--color-text-muted)]">
            Last Seen
          </div>
        </div>

        {/* Table Body */}
        <div>
          {paginatedDevices.length === 0 ? (
            <div className="px-4 py-12 text-center text-[var(--color-text-muted)] font-[var(--font-mono)]">
              {search ? 'No devices match your search' : 'No devices found'}
            </div>
          ) : (
            paginatedDevices.map((device, index) => {
              const status = getStatusVariant(device)
              return (
                <div
                  key={device.host}
                  onClick={() => onDeviceClick?.(device)}
                  className={cn(
                    'animate-fade-in-up grid grid-cols-[auto_1fr_140px_100px_100px_100px_100px] gap-4 px-4 py-3 border-b border-[var(--color-border)] last:border-b-0 hover:bg-[var(--color-surface)]/50 transition-colors cursor-pointer',
                    !device.isUp && 'bg-[var(--color-alert)]/5'
                  )}
                  style={{ animationDelay: `${index * 20}ms` }}
                >
                  {/* Status Indicator */}
                  <div className="flex items-center">
                    <StatusIndicator status={status} />
                  </div>

                  {/* Host */}
                  <div className="flex flex-col justify-center min-w-0">
                    <span className="font-[var(--font-mono)] text-sm text-[var(--color-text-primary)] truncate">
                      {device.host}
                    </span>
                    {device.description && (
                      <span className="text-xs text-[var(--color-text-muted)] truncate">
                        {device.description}
                      </span>
                    )}
                  </div>

                  {/* IP */}
                  <div className="flex items-center font-[var(--font-mono)] text-sm text-[var(--color-text-secondary)]">
                    {device.ip}
                  </div>

                  {/* Type */}
                  <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
                    {device.type && deviceIcons[device.type]}
                    <span className="text-xs uppercase font-[var(--font-display)]">
                      {device.type || '-'}
                    </span>
                  </div>

                  {/* Latency */}
                  <div className="flex items-center font-[var(--font-mono)] text-sm">
                    <span
                      className={cn(
                        device.isUp && device.latencyMs !== null
                          ? device.latencyMs > 100
                            ? 'text-[var(--color-amber)]'
                            : 'text-[var(--color-terminal)]'
                          : 'text-[var(--color-text-muted)]'
                      )}
                    >
                      {device.isUp ? formatLatency(device.latencyMs) : '-'}
                    </span>
                  </div>

                  {/* Packet Loss */}
                  <div className="flex items-center font-[var(--font-mono)] text-sm">
                    <span
                      className={cn(
                        device.isUp && device.packetLoss !== null
                          ? device.packetLoss > 0.05
                            ? 'text-[var(--color-amber)]'
                            : device.packetLoss > 0
                              ? 'text-[var(--color-text-secondary)]'
                              : 'text-[var(--color-terminal)]'
                          : 'text-[var(--color-text-muted)]'
                      )}
                    >
                      {device.isUp ? formatPacketLoss(device.packetLoss) : '-'}
                    </span>
                  </div>

                  {/* Last Seen */}
                  <div className="flex items-center font-[var(--font-mono)] text-xs text-[var(--color-text-muted)]">
                    {formatRelativeTime(device.lastSeen)}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Footer with pagination */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-[var(--color-text-muted)] font-[var(--font-mono)]">
          Showing {startIndex + 1}-{Math.min(startIndex + ITEMS_PER_PAGE, sortedDevices.length)} of {sortedDevices.length} devices
        </div>

        {totalPages > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                currentPage === 1
                  ? 'text-[var(--color-text-muted)] cursor-not-allowed'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] hover:text-[var(--color-cyan)]'
              )}
            >
              <ChevronLeft size={16} />
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => handlePageChange(page)}
                className={cn(
                  'min-w-[32px] h-8 px-2 rounded-md text-xs font-[var(--font-mono)] transition-colors',
                  page === currentPage
                    ? 'bg-[var(--color-cyan)]/20 text-[var(--color-cyan)] border border-[var(--color-cyan)]/30'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)]'
                )}
              >
                {page}
              </button>
            ))}

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                currentPage === totalPages
                  ? 'text-[var(--color-text-muted)] cursor-not-allowed'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] hover:text-[var(--color-cyan)]'
              )}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
