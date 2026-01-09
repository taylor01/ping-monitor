import { useQuery } from '@tanstack/react-query'
import { getMeasurements } from '@/api/measurements'

interface UseDeviceMeasurementsOptions {
  host: string
  since?: number // minutes, defaults to 60
  enabled?: boolean
}

export function useDeviceMeasurements({ host, since = 60, enabled = true }: UseDeviceMeasurementsOptions) {
  return useQuery({
    queryKey: ['measurements', host, since],
    queryFn: () => getMeasurements({ host, since, limit: 200 }),
    enabled: enabled && !!host,
    staleTime: 30_000, // 30 seconds
    refetchInterval: 30_000,
  })
}
