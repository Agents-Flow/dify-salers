/**
 * Lead service hooks - following Dify's useQuery pattern
 * Reference: web/service/use-apps.ts
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { del, get, patch, post } from './base'

const NAME_SPACE = 'leads'

// ===== Type Definitions =====

export type Lead = {
  id: string
  tenant_id: string
  task_id: string | null
  task_run_id: string | null
  platform: string
  platform_user_id: string | null
  platform_comment_id: string | null
  platform_video_id: string | null
  platform_user_sec_uid: string | null
  nickname: string | null
  avatar_url: string | null
  region: string | null
  comment_content: string | null
  source_video_url: string | null
  source_video_title: string | null
  reply_url: string | null
  replied_at: string | null
  reply_content: string | null
  profile_url: string | null
  intent_score: number
  intent_tags: string[] | null
  intent_reason: string | null
  status: 'new' | 'contacted' | 'converted' | 'invalid'
  contacted_at: string | null
  created_at: string
  updated_at: string
}

export type LeadTask = {
  id: string
  tenant_id: string
  name: string
  platform: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  config: {
    video_urls?: string[]
    keywords?: string[]
    comment_keywords?: string[]
    city?: string
    max_comments?: number
  }
  result_summary: Record<string, any> | null
  error_message: string | null
  total_leads: number
  created_by: string | null
  created_at: string
  updated_at: string
}

export type TaskRun = {
  id: string
  run_number: number
  status: 'running' | 'completed' | 'failed'
  started_at: string | null
  completed_at: string | null
  total_crawled: number
  total_created: number
  config_snapshot: LeadTask['config'] | null
  error_message: string | null
}

export type TaskRunsResponse = {
  data: TaskRun[]
}

export type LeadListResponse = {
  data: Lead[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

export type LeadTaskListResponse = {
  data: LeadTask[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

export type LeadStats = {
  total: number
  new: number
  contacted: number
  converted: number
  high_intent: number
}

export type LeadListParams = {
  page?: number
  limit?: number
  status?: string
  min_intent?: number
  task_id?: string
  keyword?: string
  platform?: string
}

export type LeadTaskListParams = {
  page?: number
  limit?: number
  status?: string
}

export type Platform = {
  value: string
  label: string
}

export type PlatformListResponse = {
  data: Platform[]
}

export type CreateLeadTaskData = {
  name: string
  platform?: string
  task_type?: string
  config?: {
    video_urls?: string[]
    keywords?: string[]
    city?: string
    max_comments?: number
  }
}

export type UpdateLeadData = {
  status?: string
  intent_score?: number
  intent_tags?: string[]
}

export type UpdateLeadTaskData = {
  name?: string
  platform?: string
  config?: {
    video_urls?: string[]
    keywords?: string[]
    city?: string
    max_comments?: number
  }
}

// ===== Lead Hooks =====

export const useLeadList = (params: LeadListParams = {}) => {
  return useQuery<LeadListResponse>({
    queryKey: [NAME_SPACE, 'list', params],
    queryFn: () => get<LeadListResponse>('/leads', { params }),
  })
}

export const useLead = (leadId: string, enabled = true) => {
  return useQuery<Lead>({
    queryKey: [NAME_SPACE, 'detail', leadId],
    queryFn: () => get<Lead>(`/leads/${leadId}`),
    enabled: enabled && !!leadId,
  })
}

export const useLeadStats = () => {
  return useQuery<LeadStats>({
    queryKey: [NAME_SPACE, 'stats'],
    queryFn: () => get<LeadStats>('/leads/stats'),
  })
}

export const useUpdateLead = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & UpdateLeadData) =>
      patch<Lead>(`/leads/${id}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'list'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'stats'] })
    },
  })
}

// ===== Lead Task Hooks =====

export const usePlatforms = () => {
  return useQuery<PlatformListResponse>({
    queryKey: [NAME_SPACE, 'platforms'],
    queryFn: () => get<PlatformListResponse>('/lead-platforms'),
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  })
}

export const useLeadTaskList = (params: LeadTaskListParams = {}, options?: { refetchInterval?: number | false }) => {
  return useQuery<LeadTaskListResponse>({
    queryKey: [NAME_SPACE, 'tasks', params],
    queryFn: () => get<LeadTaskListResponse>('/lead-tasks', { params }),
    refetchInterval: options?.refetchInterval,
  })
}

export const useLeadTask = (taskId: string, enabled = true) => {
  return useQuery<LeadTask>({
    queryKey: [NAME_SPACE, 'task', taskId],
    queryFn: () => get<LeadTask>(`/lead-tasks/${taskId}`),
    enabled: enabled && !!taskId,
  })
}

export const useCreateLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateLeadTaskData) =>
      post<LeadTask>('/lead-tasks', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}

export const useRunLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) =>
      post<{ result: string; message: string }>(`/lead-tasks/${taskId}/run`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}

export const useUpdateLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & UpdateLeadTaskData) =>
      patch<LeadTask>(`/lead-tasks/${id}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
    },
  })
}

export const useRestartLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, clearLeads = false }: { taskId: string; clearLeads?: boolean }) =>
      post<{ result: string; message: string }>(`/lead-tasks/${taskId}/restart`, {
        body: { clear_leads: clearLeads },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'list'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'stats'] })
    },
  })
}

export const useTaskLeads = (
  taskId: string,
  params: { page?: number; limit?: number; task_run_id?: string } = {},
  enabled = true,
) => {
  return useQuery<LeadListResponse>({
    queryKey: [NAME_SPACE, 'task-leads', taskId, params],
    queryFn: () => get<LeadListResponse>(`/lead-tasks/${taskId}/leads`, { params }),
    enabled: enabled && !!taskId,
    refetchOnWindowFocus: true,
    staleTime: 0, // Always refetch when query key changes
  })
}

export const useTaskRuns = (taskId: string, enabled = true) => {
  return useQuery<TaskRunsResponse>({
    queryKey: [NAME_SPACE, 'task-runs', taskId],
    queryFn: () => get<TaskRunsResponse>(`/lead-tasks/${taskId}/runs`),
    enabled: enabled && !!taskId,
  })
}

export const useDeleteLeadTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) =>
      del(`/lead-tasks/${taskId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'tasks'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'list'] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'stats'] })
    },
  })
}

// =============================================================================
// Social Outreach Types
// =============================================================================

export type TargetKOL = {
  id: string
  tenant_id: string
  platform: 'x' | 'instagram'
  username: string
  display_name?: string
  profile_url?: string
  bio?: string
  avatar_url?: string
  follower_count: number
  region?: string
  language: string
  niche?: string
  timezone?: string
  status: 'active' | 'paused' | 'archived'
  created_at: string
  updated_at: string
}

export type SubAccount = {
  id: string
  tenant_id: string
  platform: 'x' | 'instagram'
  username: string
  email?: string
  target_kol_id?: string
  browser_profile_id?: string
  status: 'healthy' | 'needs_verification' | 'banned' | 'cooling'
  daily_limit_follows: number
  daily_limit_dms: number
  daily_follows_used: number
  daily_dms_used: number
  lifetime_follows: number
  lifetime_dms: number
  cooling_until?: string
  last_action_at?: string
  created_at: string
  updated_at: string
}

export type FollowerTarget = {
  id: string
  tenant_id: string
  target_kol_id: string
  platform_user_id: string
  username: string
  display_name?: string
  bio?: string
  avatar_url?: string
  follower_count: number
  following_count: number
  post_count: number
  quality_tier: 'high' | 'medium' | 'low'
  status: 'new' | 'followed' | 'follow_back' | 'dm_sent' | 'replied' | 'converted' | 'unfollowed' | 'blocked'
  assigned_sub_account_id?: string
  followed_at?: string
  follow_back_at?: string
  dm_sent_at?: string
  replied_at?: string
  converted_at?: string
  created_at: string
}

export type OutreachConversation = {
  id: string
  platform: 'x' | 'instagram'
  status: 'ai_handling' | 'needs_human' | 'human_handling' | 'paused' | 'converted' | 'closed'
  follower?: {
    id: string
    username: string
    display_name?: string
    bio?: string
    avatar_url?: string
  }
  sub_account?: {
    id: string
    username: string
  }
  total_messages: number
  ai_turns: number
  human_messages: number
  conversion_score?: number
  human_reason?: string
  last_message_at?: string
  created_at: string
}

export type OutreachMessage = {
  id: string
  direction: 'inbound' | 'outbound'
  content: string
  sender_type: 'ai' | 'human' | 'follower'
  ai_intent?: string
  delivery_status?: string
  created_at: string
}

export type OutreachTask = {
  id: string
  tenant_id: string
  target_kol_id: string
  name: string
  task_type: 'follow' | 'dm' | 'follow_dm'
  platform: 'x' | 'instagram'
  status: 'pending' | 'running' | 'completed' | 'failed'
  config?: Record<string, any>
  message_templates?: string[]
  target_count: number
  processed_count: number
  success_count: number
  failed_count: number
  scheduled_at?: string
  created_at: string
}

export type DashboardOverview = {
  kols: { total: number }
  accounts: {
    total: number
    healthy: number
    health_rate: number
  }
  funnel: {
    total_followers: number
    followed: number
    follow_backs: number
    dm_sent: number
    converted: number
    follow_back_rate: number
    dm_response_rate: number
    conversion_rate: number
  }
  conversations: {
    total: number
    active: number
    needs_human: number
  }
}

export type ImportResult = {
  total_rows: number
  imported: number
  skipped: number
  errors: string[]
}

// =============================================================================
// Social Outreach Hooks - Target KOL
// =============================================================================

export const useTargetKOLList = (params: {
  page?: number
  limit?: number
  platform?: string
  status?: string
} = {}) => {
  return useQuery<{ data: TargetKOL[]; total: number; page: number; limit: number; has_more: boolean }>({
    queryKey: [NAME_SPACE, 'kols', params],
    queryFn: () => get('/target-kols', { params }),
  })
}

export const useTargetKOL = (kolId: string, enabled = true) => {
  return useQuery<TargetKOL>({
    queryKey: [NAME_SPACE, 'kol', kolId],
    queryFn: () => get(`/target-kols/${kolId}`),
    enabled: enabled && !!kolId,
  })
}

export const useCreateTargetKOL = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<TargetKOL>) =>
      post<TargetKOL>('/target-kols', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'kols'] })
    },
  })
}

export const useUpdateTargetKOL = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<TargetKOL>) =>
      patch<TargetKOL>(`/target-kols/${id}`, { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'kols'] })
    },
  })
}

export const useDeleteTargetKOL = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (kolId: string) => del(`/target-kols/${kolId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'kols'] })
    },
  })
}

export const useTargetKOLStats = (kolId: string, enabled = true) => {
  return useQuery<Record<string, any>>({
    queryKey: [NAME_SPACE, 'kol-stats', kolId],
    queryFn: () => get(`/target-kols/${kolId}/stats`),
    enabled: enabled && !!kolId,
  })
}

export const useScrapeFollowers = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ kolId, maxFollowers = 1000 }: { kolId: string; maxFollowers?: number }) =>
      post<{ result: string; created_count: number; message: string }>(
        `/target-kols/${kolId}/scrape-followers`,
        { body: { max_followers: maxFollowers } },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'follower-targets'] })
    },
  })
}

// =============================================================================
// Social Outreach Hooks - Sub-Account
// =============================================================================

export const useSubAccountList = (params: {
  page?: number
  limit?: number
  target_kol_id?: string
  platform?: string
  status?: string
} = {}) => {
  return useQuery<{ data: SubAccount[]; total: number; page: number; limit: number; has_more: boolean }>({
    queryKey: [NAME_SPACE, 'sub-accounts', params],
    queryFn: () => get('/sub-accounts', { params }),
  })
}

export const useSubAccount = (accountId: string, enabled = true) => {
  return useQuery<SubAccount>({
    queryKey: [NAME_SPACE, 'sub-account', accountId],
    queryFn: () => get(`/sub-accounts/${accountId}`),
    enabled: enabled && !!accountId,
  })
}

export const useCreateSubAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<SubAccount> & { password?: string }) =>
      post<SubAccount>('/sub-accounts', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'sub-accounts'] })
    },
  })
}

export const useImportSubAccounts = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { platform: string; csv_content: string; target_kol_id?: string }) =>
      post<ImportResult>('/sub-accounts/import', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'sub-accounts'] })
    },
  })
}

export const useDeleteSubAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (accountId: string) => del(`/sub-accounts/${accountId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'sub-accounts'] })
    },
  })
}

export const useHealthCheckSubAccount = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (accountId: string) =>
      post<{ account_id: string; previous_status: string; current_status: string; message: string }>(
        `/sub-accounts/${accountId}/health-check`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'sub-accounts'] })
    },
  })
}

export const useMarkSubAccountCooling = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, durationHours = 24, reason }: { accountId: string; durationHours?: number; reason?: string }) =>
      post(`/sub-accounts/${accountId}/cooling`, { body: { duration_hours: durationHours, reason } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'sub-accounts'] })
    },
  })
}

// =============================================================================
// Social Outreach Hooks - Follower Targets
// =============================================================================

export const useFollowerTargetList = (params: {
  page?: number
  limit?: number
  target_kol_id?: string
  status?: string
  quality_tier?: string
} = {}) => {
  return useQuery<{ data: FollowerTarget[]; total: number; page: number; limit: number; has_more: boolean }>({
    queryKey: [NAME_SPACE, 'follower-targets', params],
    queryFn: () => get('/follower-targets', { params }),
  })
}

export const useFunnelStats = (targetKolId?: string) => {
  return useQuery<{
    new: number
    followed: number
    follow_back: number
    dm_sent: number
    replied: number
    converted: number
  }>({
    queryKey: [NAME_SPACE, 'funnel-stats', targetKolId],
    queryFn: () => get('/follower-targets/funnel-stats', { params: { target_kol_id: targetKolId } }),
  })
}

// =============================================================================
// Social Outreach Hooks - Outreach Tasks
// =============================================================================

export const useOutreachTaskList = (params: {
  page?: number
  limit?: number
  target_kol_id?: string
  status?: string
} = {}) => {
  return useQuery<{ data: OutreachTask[]; total: number; page: number; limit: number; has_more: boolean }>({
    queryKey: [NAME_SPACE, 'outreach-tasks', params],
    queryFn: () => get('/outreach-tasks', { params }),
  })
}

export const useCreateOutreachTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<OutreachTask>) =>
      post<OutreachTask>('/outreach-tasks', { body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'outreach-tasks'] })
    },
  })
}

export const useStartOutreachTask = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) =>
      post<{ result: string; message: string }>(`/outreach-tasks/${taskId}/start`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'outreach-tasks'] })
    },
  })
}

// =============================================================================
// Social Outreach Hooks - Conversations (Unified Inbox)
// =============================================================================

export const useConversationList = (params: {
  page?: number
  limit?: number
  status?: string
  target_kol_id?: string
  platform?: string
  needs_attention?: string
} = {}, options?: { refetchInterval?: number | false }) => {
  return useQuery<{ data: OutreachConversation[]; total: number; page: number; limit: number; has_more: boolean }>({
    queryKey: [NAME_SPACE, 'conversations', params],
    queryFn: () => get('/conversations', { params }),
    refetchInterval: options?.refetchInterval,
  })
}

export const useConversation = (conversationId: string, enabled = true) => {
  return useQuery<OutreachConversation & { messages: OutreachMessage[] }>({
    queryKey: [NAME_SPACE, 'conversation', conversationId],
    queryFn: () => get(`/conversations/${conversationId}`),
    enabled: enabled && !!conversationId,
  })
}

export const useUpdateConversationStatus = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status, reason }: { id: string; status: string; reason?: string }) =>
      patch<OutreachConversation>(`/conversations/${id}/status`, { body: { status, reason } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'conversations'] })
    },
  })
}

export const useSendMessage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ conversationId, content, senderType = 'human' }: {
      conversationId: string
      content: string
      senderType?: 'human' | 'ai'
    }) =>
      post<OutreachMessage>(`/conversations/${conversationId}/messages`, {
        body: { content, sender_type: senderType },
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'conversation', variables.conversationId] })
      queryClient.invalidateQueries({ queryKey: [NAME_SPACE, 'conversations'] })
    },
  })
}

export const useGenerateAIReply = () => {
  return useMutation({
    mutationFn: (conversationId: string) =>
      post<{
        content: string
        intent: string
        confidence: number
        needs_human: boolean
        conversion_score: number
      }>(`/conversations/${conversationId}/ai-reply`),
  })
}

// =============================================================================
// Social Outreach Hooks - Dashboard
// =============================================================================

export const useDashboardOverview = (targetKolId?: string) => {
  return useQuery<DashboardOverview>({
    queryKey: [NAME_SPACE, 'dashboard', targetKolId],
    queryFn: () => get('/dashboard/overview', { params: { target_kol_id: targetKolId } }),
  })
}

export const useAIStatus = () => {
  return useQuery<{
    conversation_ai: { enabled: boolean; configured: boolean }
    follower_scraper: { enabled: boolean; configured: boolean }
  }>({
    queryKey: [NAME_SPACE, 'ai-status'],
    queryFn: () => get('/dashboard/ai-status'),
  })
}

export const useScraperStatus = () => {
  return useQuery<{ configured: boolean; enabled: boolean; has_token: boolean }>({
    queryKey: [NAME_SPACE, 'scraper-status'],
    queryFn: () => get('/scraper/status'),
  })
}

// ===== Utility Functions =====

export const getIntentLevel = (score: number): 'high' | 'medium' | 'low' | 'unknown' => {
  if (score >= 70)
    return 'high'
  if (score >= 40)
    return 'medium'
  if (score > 0)
    return 'low'
  return 'unknown'
}

export const getIntentColor = (score: number): string => {
  if (score >= 70)
    return 'text-util-colors-green-green-600'
  if (score >= 40)
    return 'text-util-colors-orange-orange-600'
  if (score > 0)
    return 'text-util-colors-gray-gray-600'
  return 'text-text-tertiary'
}

export const getStatusColor = (status: Lead['status']): 'blue' | 'orange' | 'green' | 'gray' => {
  const colors: Record<Lead['status'], 'blue' | 'orange' | 'green' | 'gray'> = {
    new: 'blue',
    contacted: 'orange',
    converted: 'green',
    invalid: 'gray',
  }
  return colors[status]
}

export const getTaskStatusColor = (status: LeadTask['status']): 'gray' | 'blue' | 'green' | 'red' => {
  const colors: Record<LeadTask['status'], 'gray' | 'blue' | 'green' | 'red'> = {
    pending: 'gray',
    running: 'blue',
    completed: 'green',
    failed: 'red',
  }
  return colors[status]
}
