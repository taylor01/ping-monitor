import apiClient from './client'
import type { Measurement } from '@/types/api'

interface MeasurementsApiResponse {
  data: Array<{
    id: string
    type: string
    attributes: {
      host: string
      ip: string
      timestamp: string
      is_up: boolean
      latency_ms: number | null
      packet_loss: number | null
      jitter_ms: number | null
    }
  }>
}

interface GetMeasurementsParams {
  host?: string
  since?: number // minutes
  limit?: number
}

export async function getMeasurements(params: GetMeasurementsParams = {}): Promise<Measurement[]> {
  const searchParams = new URLSearchParams()
  if (params.host) searchParams.set('host', params.host)
  if (params.since) searchParams.set('since', params.since.toString())
  if (params.limit) searchParams.set('limit', params.limit.toString())

  const url = `/measurements${searchParams.toString() ? `?${searchParams}` : ''}`
  const response = await apiClient.get<MeasurementsApiResponse>(url)

  return response.data.data.map((m) => ({
    id: m.id,
    host: m.attributes.host,
    ip: m.attributes.ip,
    timestamp: m.attributes.timestamp,
    isUp: m.attributes.is_up,
    latencyMs: m.attributes.latency_ms,
    packetLoss: m.attributes.packet_loss,
    jitterMs: m.attributes.jitter_ms,
  }))
}
