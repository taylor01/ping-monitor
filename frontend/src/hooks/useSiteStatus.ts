import { useQuery } from '@tanstack/react-query'
import { getSiteStatus } from '@/api/sites'

const POLL_INTERVAL = 10_000 // 10 seconds

export function useSiteStatus(siteId: string) {
  return useQuery({
    queryKey: ['site-status', siteId],
    queryFn: () => getSiteStatus(siteId),
    enabled: !!siteId, // Don't fetch until we have a site ID
    refetchInterval: POLL_INTERVAL,
    staleTime: 5_000,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}
