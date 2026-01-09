// JSON:API response wrapper types
export interface JsonApiResponse<T> {
  data: T
  included?: JsonApiResource[]
  meta?: Record<string, unknown>
}

export interface JsonApiResource {
  id: string
  type: string
  attributes: Record<string, unknown>
  relationships?: Record<string, { data: { id: string; type: string } | { id: string; type: string }[] }>
}

// Device/Host types
export type DeviceType =
  | 'router'
  | 'switch'
  | 'ap'
  | 'camera'
  | 'nas'
  | 'server'
  | 'bridge'
  | 'iot'
  | 'safety'
  | 'media'
  | 'power'
  | 'viewport'
  | 'external'
  | 'ups'

export interface DeviceStatus {
  host: string
  ip: string
  type?: DeviceType
  description?: string
  isUp: boolean
  latencyMs: number | null
  packetLoss: number | null
  jitterMs?: number | null
  lastSeen?: string
}

// Site status from GET /api/v1/sites/:id/status
export interface SiteStatus {
  name: string
  status: 'healthy' | 'degraded' | 'critical' | 'offline'
  devicesTotal: number
  devicesUp: number
  devicesDown: number
  activeAnomalies: number
  lastDataAt: string | null
  devices: DeviceStatus[]
}

// Measurement from GET /api/v1/measurements
export interface Measurement {
  id: string
  host: string
  ip: string
  timestamp: string
  isUp: boolean
  latencyMs: number | null
  packetLoss: number | null
  jitterMs: number | null
}

// Anomaly from GET /api/v1/anomalies
export type AnomalyType =
  | 'host_down'
  | 'host_recovery'
  | 'latency_spike'
  | 'packet_loss'
  | 'site_offline'

export type AnomalySeverity = 'info' | 'warning' | 'critical'

export interface Anomaly {
  id: string
  host: string
  hostIp?: string
  anomalyType: AnomalyType
  severity: AnomalySeverity
  message: string
  currentValue: number | null
  baselineValue: number | null
  active: boolean
  duration: string | null
  resolvedAt: string | null
  createdAt: string
}

// Baseline from GET /api/v1/baselines
export interface Baseline {
  host: string
  ip: string
  latencyMean: number
  latencyStddev: number
  latencyP95: number
  latencyP99: number
  sampleCount: number
  thresholds: {
    warning: number
    critical: number
  }
}

// Site from GET /api/v1/sites
export interface Site {
  id: string
  name: string
  status: string
  healthy: boolean
  hostsCount: number
  lastHeartbeat: string | null
}

// Auth types
export interface AuthTokenResponse {
  accessToken: string
  refreshToken: string
  expiresIn: number
}
