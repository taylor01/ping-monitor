import apiClient from './client'
import type { SiteStatus, DeviceStatus } from '@/types/api'

interface SiteStatusApiResponse {
  data: {
    id: string
    type: string
    attributes: {
      name: string
      status: string
      devices_total: number
      devices_up: number
      devices_down: number
      active_anomalies: number
      last_data_at: string | null
      devices: Array<{
        host: string
        ip: string
        type?: string
        description?: string
        is_up: boolean
        latency_ms: number | null
        packet_loss: number | null
        jitter_ms?: number | null
        last_seen?: string
      }>
    }
  }
}

export async function getSiteStatus(siteId: string): Promise<SiteStatus> {
  const response = await apiClient.get<SiteStatusApiResponse>(`/sites/${siteId}/status`)
  const attrs = response.data.data.attributes

  return {
    name: attrs.name,
    status: attrs.status as SiteStatus['status'],
    devicesTotal: attrs.devices_total,
    devicesUp: attrs.devices_up,
    devicesDown: attrs.devices_down,
    activeAnomalies: attrs.active_anomalies,
    lastDataAt: attrs.last_data_at,
    devices: attrs.devices.map((d): DeviceStatus => ({
      host: d.host,
      ip: d.ip,
      type: d.type as DeviceStatus['type'],
      description: d.description,
      isUp: d.is_up,
      latencyMs: d.latency_ms,
      packetLoss: d.packet_loss,
      jitterMs: d.jitter_ms,
      lastSeen: d.last_seen,
    })),
  }
}

interface SitesListApiResponse {
  data: Array<{
    id: string
    type: string
    attributes: {
      name: string
      status: string
      healthy: boolean
      hosts_count: number
      last_heartbeat: string | null
    }
  }>
}

export interface SiteListItem {
  id: string
  name: string
  status: string
  healthy: boolean
  hostsCount: number
  lastHeartbeat: string | null
}

export async function getSites(): Promise<SiteListItem[]> {
  const response = await apiClient.get<SitesListApiResponse>('/sites')
  return response.data.data.map((site) => ({
    id: site.id,
    name: site.attributes.name,
    status: site.attributes.status,
    healthy: site.attributes.healthy,
    hostsCount: site.attributes.hosts_count,
    lastHeartbeat: site.attributes.last_heartbeat,
  }))
}
