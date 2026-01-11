import { useQueries } from '@tanstack/react-query'
import { getSiteStatus } from '@/api/sites'
import type { Site, SiteStatus } from '@/types/api'

const POLL_INTERVAL = 15_000 // 15 seconds for overview

export interface SiteWithStatus extends Site {
  siteStatus: SiteStatus | null
  isLoading: boolean
  error: Error | null
}

export function useAllSiteStatuses(sites: Site[] | undefined) {
  const queries = useQueries({
    queries: (sites || []).map((site) => ({
      queryKey: ['site-status', site.id],
      queryFn: () => getSiteStatus(site.id),
      refetchInterval: POLL_INTERVAL,
      staleTime: 10_000,
      retry: 2,
    })),
  })

  const sitesWithStatus: SiteWithStatus[] = (sites || []).map((site, index) => ({
    ...site,
    siteStatus: queries[index]?.data ?? null,
    isLoading: queries[index]?.isLoading ?? true,
    error: queries[index]?.error as Error | null,
  }))

  const isLoading = queries.some((q) => q.isLoading)
  const isRefetching = queries.some((q) => q.isRefetching)

  return {
    sites: sitesWithStatus,
    isLoading,
    isRefetching,
  }
}
