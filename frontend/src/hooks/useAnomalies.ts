import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAnomalies, resolveAnomaly } from '@/api/anomalies'
import type { AnomalySeverity } from '@/types/api'

const POLL_INTERVAL = 15_000 // 15 seconds

interface UseAnomaliesParams {
  status?: 'active' | 'resolved' | 'all'
  severity?: AnomalySeverity
  limit?: number
}

export function useAnomalies(params: UseAnomaliesParams = { status: 'active' }) {
  return useQuery({
    queryKey: ['anomalies', params],
    queryFn: () => getAnomalies(params),
    refetchInterval: POLL_INTERVAL,
    staleTime: 5_000,
  })
}

export function useResolveAnomaly() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: resolveAnomaly,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
    },
  })
}
