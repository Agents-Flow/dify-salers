import { useMutation, useQuery } from '@tanstack/react-query'
import { get, post, put } from './base'

// =============================================================================
// Types
// =============================================================================

export type LeadsConfigSchema = {
  label: string
  description: string
  is_encrypted: boolean
  fields: Array<{
    name: string
    type: string
    required?: boolean
    default?: unknown
    options?: string[]
  }>
}

export type LeadsConfigsResponse = {
  configs: Record<string, Record<string, unknown>>
  schema: Record<string, LeadsConfigSchema>
}

export type WorkflowBinding = {
  id: string
  action_type: string
  app_id: string
  app_mode: string
  is_enabled: boolean
  config: Record<string, unknown>
  created_at: string | null
}

export type ActionType = {
  value: string
  label: string
  description: string
}

export type WorkflowBindingsResponse = {
  bindings: WorkflowBinding[]
  action_types: ActionType[]
}

export type AvailableApp = {
  id: string
  name: string
  mode: string
  icon: string
  icon_type: string
  icon_background: string
}

export type TestConnectionResult = {
  success: boolean
  message: string
  username?: string
}

// =============================================================================
// Config Hooks
// =============================================================================

export const useLeadsConfigs = () => {
  return useQuery({
    queryKey: ['leads', 'configs'],
    queryFn: () => get<LeadsConfigsResponse>('/leads/configs'),
  })
}

export const useLeadsConfig = (configKey: string) => {
  return useQuery({
    queryKey: ['leads', 'configs', configKey],
    queryFn: () => get<{ config_key: string; config_value: Record<string, unknown> | null }>(`/leads/configs/${configKey}`),
    enabled: !!configKey,
  })
}

export const useUpdateLeadsConfig = () => {
  return useMutation({
    mutationFn: ({ configKey, configValue }: { configKey: string; configValue: Record<string, unknown> }) =>
      put<{ result: string }>(`/leads/configs/${configKey}`, { body: { config_value: configValue } }),
  })
}

export const useDeleteLeadsConfig = () => {
  return useMutation({
    mutationFn: (configKey: string) =>
      fetch(`/console/api/leads/configs/${configKey}`, { method: 'DELETE' }),
  })
}

export const useTestConnection = () => {
  return useMutation({
    mutationFn: () => post<TestConnectionResult>('/leads/configs/test-connection'),
  })
}

// =============================================================================
// Workflow Binding Hooks
// =============================================================================

export const useWorkflowBindings = () => {
  return useQuery({
    queryKey: ['leads', 'workflow-bindings'],
    queryFn: () => get<WorkflowBindingsResponse>('/leads/workflow-bindings'),
  })
}

export const useCreateWorkflowBinding = () => {
  return useMutation({
    mutationFn: (data: { action_type: string; app_id: string; app_mode: string; config?: Record<string, unknown> }) =>
      post<WorkflowBinding>('/leads/workflow-bindings', { body: data }),
  })
}

export const useDeleteWorkflowBinding = () => {
  return useMutation({
    mutationFn: (actionType: string) =>
      fetch(`/console/api/leads/workflow-bindings/${actionType}`, { method: 'DELETE' }),
  })
}

export const useToggleWorkflowBinding = () => {
  return useMutation({
    mutationFn: ({ actionType, isEnabled }: { actionType: string; isEnabled: boolean }) =>
      post<{ result: string; is_enabled: boolean }>(`/leads/workflow-bindings/${actionType}/toggle`, {
        body: { is_enabled: isEnabled },
      }),
  })
}

export const useAvailableApps = () => {
  return useQuery({
    queryKey: ['leads', 'available-apps'],
    queryFn: () => get<{ apps: AvailableApp[]; total: number }>('/leads/available-apps'),
  })
}
