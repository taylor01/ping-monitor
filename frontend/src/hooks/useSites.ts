import { useQuery } from '@tanstack/react-query'
import { getSites } from '@/api/sites'

export function useSites() {
  return useQuery({
    queryKey: ['sites'],
    queryFn: getSites,
    staleTime: 60_000, // 1 minute
  })
}

export function useSiteByName(name: string) {
  const { data: sites, ...rest } = useSites()
  const site = sites?.find((s) => s.name === name)
  return { site, sites, ...rest }
}
