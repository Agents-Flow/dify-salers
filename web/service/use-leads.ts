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
  platform: string
  platform_user_id: string | null
  nickname: string | null
  avatar_url: string | null
  region: string | null
  comment_content: string | null
  source_video_url: string | null
  source_video_title: string | null
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

export const useTaskLeads = (taskId: string, params: { page?: number; limit?: number } = {}, enabled = true) => {
  return useQuery<LeadListResponse>({
    queryKey: [NAME_SPACE, 'task-leads', taskId, params],
    queryFn: () => get<LeadListResponse>(`/lead-tasks/${taskId}/leads`, { params }),
    enabled: enabled && !!taskId,
    refetchOnWindowFocus: true,
    staleTime: 0, // Always refetch when query key changes
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
