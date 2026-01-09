import apiClient from './client'
import type { Anomaly, AnomalyType, AnomalySeverity } from '@/types/api'

interface AnomaliesApiResponse {
  data: Array<{
    id: string
    type: string
    attributes: {
      host: string
      host_ip?: string
      anomaly_type: string
      severity: string
      message: string
      current_value: number | null
      baseline_value: number | null
      active: boolean
      duration: string | null
      resolved_at: string | null
      created_at: string
    }
  }>
  meta?: {
    total: number
    active: number
    resolved: number
  }
}

interface GetAnomaliesParams {
  status?: 'active' | 'resolved' | 'all'
  severity?: AnomalySeverity
  limit?: number
  since?: string
}

export async function getAnomalies(params: GetAnomaliesParams = {}): Promise<Anomaly[]> {
  const queryParams = new URLSearchParams()
  if (params.status) queryParams.set('status', params.status)
  if (params.severity) queryParams.set('severity', params.severity)
  if (params.limit) queryParams.set('limit', params.limit.toString())
  if (params.since) queryParams.set('since', params.since)

  const url = `/anomalies${queryParams.toString() ? `?${queryParams}` : ''}`
  const response = await apiClient.get<AnomaliesApiResponse>(url)

  return response.data.data.map((a) => ({
    id: a.id,
    host: a.attributes.host,
    hostIp: a.attributes.host_ip,
    anomalyType: a.attributes.anomaly_type as AnomalyType,
    severity: a.attributes.severity as AnomalySeverity,
    message: a.attributes.message,
    currentValue: a.attributes.current_value,
    baselineValue: a.attributes.baseline_value,
    active: a.attributes.active,
    duration: a.attributes.duration,
    resolvedAt: a.attributes.resolved_at,
    createdAt: a.attributes.created_at,
  }))
}

export async function resolveAnomaly(id: string): Promise<void> {
  await apiClient.patch(`/anomalies/${id}/resolve`)
}
