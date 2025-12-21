import { useQuery } from '@tanstack/react-query'
import { get } from './base'

// =============================================================================
// Types
// =============================================================================

export type FunnelData = {
  total_followers: number
  followed: number
  follow_backs: number
  dm_sent: number
  converted: number
  follow_back_rate: number
  dm_response_rate: number
  conversion_rate: number
}

export type DashboardOverview = {
  kols: {
    total: number
    active: number
  }
  accounts: {
    total: number
    healthy: number
    health_rate: number
  }
  conversations: {
    total: number
    active: number
    needs_human: number
  }
  funnel: FunnelData
}

export type KOLPerformance = {
  kol_id: string
  username: string
  platform: string
  follower_count: number
  scraped_followers: number
  conversions: number
  conversion_rate: number
}

export type AccountHealth = {
  status: string
  count: number
}

export type DailyStat = {
  date: string
  scraped: number
  followed: number
  dm_sent: number
  converted: number
}

export type TaskSummary = {
  total_tasks: number
  completed: number
  running: number
  failed: number
  total_processed: number
  total_success: number
  success_rate: number
}

export type AIStatus = {
  conversation_ai: {
    enabled: boolean
    configured: boolean
  }
  follower_scraper: {
    enabled: boolean
    configured: boolean
  }
}

// =============================================================================
// Analytics Hooks
// =============================================================================

export const useAnalyticsOverview = () => {
  return useQuery({
    queryKey: ['leads', 'analytics', 'overview'],
    queryFn: () => get<DashboardOverview>('/leads/analytics/overview'),
  })
}

export const useAnalyticsFunnel = (targetKolId?: string) => {
  return useQuery({
    queryKey: ['leads', 'analytics', 'funnel', targetKolId],
    queryFn: () => {
      const url = targetKolId
        ? `/leads/analytics/funnel?target_kol_id=${targetKolId}`
        : '/leads/analytics/funnel'
      return get<FunnelData>(url)
    },
  })
}

export const useAnalyticsKOLPerformance = () => {
  return useQuery({
    queryKey: ['leads', 'analytics', 'kol-performance'],
    queryFn: () => get<{ data: KOLPerformance[] }>('/leads/analytics/kol-performance'),
  })
}

export const useAnalyticsAccountHealth = (days = 7) => {
  return useQuery({
    queryKey: ['leads', 'analytics', 'account-health', days],
    queryFn: () => get<{ data: AccountHealth[] }>(`/leads/analytics/account-health?days=${days}`),
  })
}

export const useAnalyticsDailyStats = (days = 30) => {
  return useQuery({
    queryKey: ['leads', 'analytics', 'daily-stats', days],
    queryFn: () => get<{ data: DailyStat[] }>(`/leads/analytics/daily-stats?days=${days}`),
  })
}

export const useAnalyticsTaskSummary = () => {
  return useQuery({
    queryKey: ['leads', 'analytics', 'task-summary'],
    queryFn: () => get<TaskSummary>('/leads/analytics/task-summary'),
  })
}

export const useAIStatus = () => {
  return useQuery({
    queryKey: ['leads', 'ai-status'],
    queryFn: () => get<AIStatus>('/leads/ai-status'),
  })
}
