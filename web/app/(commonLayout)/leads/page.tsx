/**
 * Leads Page - Lead acquisition management
 * Following Dify's Apps list page pattern
 * Reference: web/app/components/apps/list.tsx
 */
'use client'
import type { FC } from 'react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from 'next/navigation'
import {
  RiAddLine,
  RiArrowLeftLine,
  RiDeleteBinLine,
  RiEdit2Line,
  RiEyeLine,
  RiPlayLine,
  RiRefreshLine,
  RiRestartLine,
} from '@remixicon/react'
import {
  getIntentColor,
  useCreateLeadTask,
  useDeleteLeadTask,
  useLeadList,
  useLeadStats,
  useLeadTaskList,
  usePlatforms,
  useRestartLeadTask,
  useRunLeadTask,
  useTaskLeads,
  useTaskRuns,
  useUpdateLead,
  useUpdateLeadTask,
} from '@/service/use-leads'
import type { CreateLeadTaskData, Lead, LeadTask, TaskRun, UpdateLeadTaskData } from '@/service/use-leads'
import { useAppContext } from '@/context/app-context'

// Status color utilities
const getStatusClassName = (status: Lead['status']): string => {
  const classes: Record<Lead['status'], string> = {
    new: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    contacted: 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600',
    converted: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    invalid: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
  }
  return classes[status]
}

const getTaskStatusClassName = (status: LeadTask['status']): string => {
  const classes: Record<LeadTask['status'], string> = {
    pending: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
    running: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    completed: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    failed: 'bg-util-colors-red-red-50 text-util-colors-red-red-600',
  }
  return classes[status]
}
import useDocumentTitle from '@/hooks/use-document-title'
// Reuse Dify base components
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import Modal from '@/app/components/base/modal'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'
import Confirm from '@/app/components/base/confirm'
import Pagination from '@/app/components/base/pagination'

// Task Form Component (Create/Edit)
type TaskFormPropsCreate = {
  onSubmit: (data: CreateLeadTaskData) => void
  onCancel: () => void
  isLoading: boolean
  initialData?: undefined
  mode: 'create'
}

type TaskFormPropsEdit = {
  onSubmit: (data: UpdateLeadTaskData) => void
  onCancel: () => void
  isLoading: boolean
  initialData: LeadTask
  mode: 'edit'
}

type TaskFormProps = TaskFormPropsCreate | TaskFormPropsEdit

const TaskForm: FC<TaskFormProps> = (props) => {
  const { onCancel, isLoading, mode } = props
  const initialData = mode === 'edit' ? props.initialData : undefined
  const { t } = useTranslation()
  const { data: platformsData } = usePlatforms()
  const [name, setName] = useState(initialData?.name || '')
  const [platform, setPlatform] = useState(initialData?.platform || 'douyin')
  const [videoUrl, setVideoUrl] = useState(initialData?.config?.video_urls?.[0] || '')
  const [keywords, setKeywords] = useState(initialData?.config?.keywords?.join(', ') || '')
  const [city, setCity] = useState(initialData?.config?.city || '')

  const platforms = platformsData?.data || [
    { value: 'douyin', label: '抖音 (Douyin)' },
    { value: 'xiaohongshu', label: '小红书 (Xiaohongshu)' },
    { value: 'kuaishou', label: '快手 (Kuaishou)' },
    { value: 'bilibili', label: 'B站 (Bilibili)' },
    { value: 'weibo', label: '微博 (Weibo)' },
  ]

  const handleSubmit = () => {
    if (!name.trim()) {
      Toast.notify({ type: 'error', message: t('leads.createTask.nameRequired') })
      return
    }

    const videoUrls = videoUrl.trim() ? [videoUrl.trim()] : []
    const keywordList = keywords.trim() ? keywords.split(',').map(k => k.trim()).filter(Boolean) : []

    if (mode === 'create') {
      (props as TaskFormPropsCreate).onSubmit({
        name: name.trim(),
        platform,
        task_type: 'comment_crawl',
        config: {
          video_urls: videoUrls,
          keywords: keywordList,
          city: city.trim() || undefined,
          max_comments: 500,
        },
      })
    }
    else {
      (props as TaskFormPropsEdit).onSubmit({
        name: name.trim(),
        platform,
        config: {
          video_urls: videoUrls,
          keywords: keywordList,
          city: city.trim() || undefined,
          max_comments: initialData?.config?.max_comments || 500,
        },
      })
    }
  }

  return (
    <div className='space-y-4 p-6'>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.task.name')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <Input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder={t('leads.createTask.namePlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.createTask.platform')}
        </label>
        <select
          value={platform}
          onChange={e => setPlatform(e.target.value)}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary focus:border-components-input-border-active focus:outline-none'
        >
          {platforms.map(p => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.createTask.videoUrl')}
        </label>
        <Input
          value={videoUrl}
          onChange={e => setVideoUrl(e.target.value)}
          placeholder={t('leads.createTask.videoUrlPlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.createTask.keywords')}
        </label>
        <Input
          value={keywords}
          onChange={e => setKeywords(e.target.value)}
          placeholder={t('leads.createTask.keywordsPlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.createTask.city')}
        </label>
        <Input
          value={city}
          onChange={e => setCity(e.target.value)}
          placeholder={t('leads.createTask.cityPlaceholder')}
        />
      </div>
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>
          {t('leads.createTask.cancel')}
        </Button>
        <Button
          variant='primary'
          onClick={handleSubmit}
          disabled={!name.trim()}
          loading={isLoading}
        >
          {mode === 'create' ? t('leads.createTask.submit') : t('leads.editTask.save')}
        </Button>
      </div>
    </div>
  )
}

// Task Detail View Component
type TaskDetailViewProps = {
  task: LeadTask
  onBack: () => void
  onEdit: () => void
  onRestart: (clearLeads: boolean) => void
  isRestarting: boolean
}

const TaskDetailView: FC<TaskDetailViewProps> = ({ task, onBack, onEdit, onRestart, isRestarting }) => {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  const [showRestartConfirm, setShowRestartConfirm] = useState(false)
  const [clearLeadsOnRestart, setClearLeadsOnRestart] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState<string>('')

  // Fetch execution history
  const { data: runsData } = useTaskRuns(task.id)

  const { data: leadsData, isLoading, refetch } = useTaskLeads(
    task.id,
    { page, limit: 20, task_run_id: selectedRunId || undefined },
  )

  // Refetch leads when task status changes to completed
  useEffect(() => {
    if (task.status === 'completed' && task.total_leads > 0)
      refetch()
  }, [task.status, task.total_leads, refetch])

  const canEdit = task.status !== 'running'
  const canRestart = task.status === 'completed' || task.status === 'failed'

  const formatRunLabel = (run: TaskRun) => {
    const date = run.started_at ? new Date(run.started_at).toLocaleString() : ''
    return `#${run.run_number} - ${date} (${run.total_created} ${t('leads.task.leads')})`
  }

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center gap-3'>
          <Button variant='ghost' size='small' onClick={onBack}>
            <RiArrowLeftLine className='h-4 w-4' />
          </Button>
          <h2 className='text-lg font-semibold text-text-primary'>{task.name}</h2>
          <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getTaskStatusClassName(task.status)}`}>
            {t(`leads.taskStatus.${task.status}`)}
          </span>
        </div>
        <div className='flex items-center gap-2'>
          {canEdit && (
            <Button variant='secondary' size='small' onClick={onEdit}>
              <RiEdit2Line className='mr-1 h-3 w-3' />
              {t('leads.task.edit')}
            </Button>
          )}
          {canRestart && (
            <Button
              variant='primary'
              size='small'
              onClick={() => setShowRestartConfirm(true)}
              loading={isRestarting}
            >
              <RiRestartLine className='mr-1 h-3 w-3' />
              {t('leads.task.restart')}
            </Button>
          )}
        </div>
      </div>

      {/* Task Info */}
      <div className='grid grid-cols-2 gap-4 rounded-lg border border-divider-subtle bg-components-panel-bg p-4 md:grid-cols-4'>
        <div>
          <div className='text-xs text-text-tertiary'>{t('leads.task.platform')}</div>
          <div className='text-sm text-text-secondary'>{task.platform}</div>
        </div>
        <div>
          <div className='text-xs text-text-tertiary'>{t('leads.task.type')}</div>
          <div className='text-sm text-text-secondary'>{t(`leads.taskType.${task.task_type}`)}</div>
        </div>
        <div>
          <div className='text-xs text-text-tertiary'>{t('leads.task.totalLeads')}</div>
          <div className='text-sm font-medium text-text-secondary'>{task.total_leads}</div>
        </div>
        <div>
          <div className='text-xs text-text-tertiary'>{t('leads.task.createdAt')}</div>
          <div className='text-sm text-text-secondary'>{task.created_at ? new Date(task.created_at).toLocaleString() : '-'}</div>
        </div>
      </div>

      {/* Config Info */}
      <div className='rounded-lg border border-divider-subtle bg-components-panel-bg p-4'>
        <div className='mb-2 text-sm font-medium text-text-secondary'>{t('leads.task.config')}</div>
        <div className='space-y-2 text-sm text-text-tertiary'>
          {task.config?.video_urls?.length ? (
            <div>{t('leads.createTask.videoUrl')}: {task.config.video_urls.join(', ')}</div>
          ) : null}
          {task.config?.keywords?.length ? (
            <div>{t('leads.createTask.keywords')}: {task.config.keywords.join(', ')}</div>
          ) : null}
          {task.config?.city ? (
            <div>{t('leads.createTask.city')}: {task.config.city}</div>
          ) : null}
        </div>
      </div>

      {/* Error Message */}
      {task.error_message && (
        <div className='rounded-lg border border-util-colors-red-red-200 bg-util-colors-red-red-50 p-4'>
          <div className='text-sm font-medium text-util-colors-red-red-600'>{t('leads.task.error')}</div>
          <div className='mt-1 text-sm text-util-colors-red-red-600'>{task.error_message}</div>
        </div>
      )}

      {/* Leads List */}
      <div>
        <div className='mb-3 flex items-center justify-between'>
          <h3 className='text-sm font-medium text-text-secondary'>{t('leads.task.collectedLeads')}</h3>
          {runsData && runsData.data.length > 0 && (
            <div className='flex items-center gap-2'>
              <span className='text-xs text-text-tertiary'>{t('leads.task.executionHistory')}:</span>
              <select
                value={selectedRunId}
                onChange={(e) => {
                  setSelectedRunId(e.target.value)
                  setPage(1)
                }}
                className='h-8 rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-2 text-xs text-text-secondary focus:border-components-input-border-active focus:outline-none'
              >
                <option value=''>{t('leads.task.allRuns')}</option>
                {runsData.data.map(run => (
                  <option key={run.id} value={run.id}>
                    {formatRunLabel(run)}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        {isLoading
          ? (
            <div className='flex h-[200px] items-center justify-center'>
              <Loading type='area' />
            </div>
          )
          : (
            <>
              <div className='rounded-xl border border-divider-subtle bg-components-panel-bg'>
                <table className='w-full'>
                  <thead>
                    <tr className='border-b border-divider-subtle'>
                      <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.nickname')}</th>
                      <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.comment')}</th>
                      <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.region')}</th>
                      <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.intentScore')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leadsData?.data?.map((lead: Lead) => (
                      <tr key={lead.id} className='border-b border-divider-subtle last:border-0'>
                        <td className='px-4 py-3 text-sm text-text-secondary'>{lead.nickname || '-'}</td>
                        <td className='max-w-[400px] truncate px-4 py-3 text-sm text-text-secondary' title={lead.comment_content || ''}>
                          {lead.comment_content || '-'}
                        </td>
                        <td className='px-4 py-3 text-sm text-text-tertiary'>{lead.region || '-'}</td>
                        <td className='px-4 py-3'>
                          <span className={`text-sm ${getIntentColor(lead.intent_score)}`}>{lead.intent_score}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(!leadsData?.data || leadsData.data.length === 0) && (
                  <div className='py-8 text-center text-text-tertiary'>
                    {t('leads.empty.taskLeads')}
                  </div>
                )}
              </div>
              {leadsData && leadsData.total > 20 && (
                <Pagination
                  className='mt-4'
                  current={page - 1}
                  onChange={p => setPage(p + 1)}
                  total={leadsData.total}
                  limit={20}
                />
              )}
            </>
          )}
      </div>

      {/* Restart Confirmation */}
      <Modal
        isShow={showRestartConfirm}
        onClose={() => setShowRestartConfirm(false)}
        title={t('leads.confirm.restartTask')}
        className='!max-w-[400px]'
      >
        <div className='p-6'>
          <p className='mb-4 text-text-secondary'>{t('leads.confirm.restartTaskDescription')}</p>
          <label className='flex items-center gap-2 text-sm text-text-secondary'>
            <input
              type='checkbox'
              checked={clearLeadsOnRestart}
              onChange={e => setClearLeadsOnRestart(e.target.checked)}
              className='rounded border-divider-regular'
            />
            {t('leads.confirm.clearLeadsOnRestart')}
          </label>
          <div className='mt-6 flex justify-end gap-2'>
            <Button variant='secondary' onClick={() => setShowRestartConfirm(false)}>
              {t('common.operation.cancel')}
            </Button>
            <Button
              variant='primary'
              onClick={() => {
                onRestart(clearLeadsOnRestart)
                setShowRestartConfirm(false)
              }}
              loading={isRestarting}
            >
              {t('leads.task.restart')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

const LeadsPage: FC = () => {
  const { t } = useTranslation()
  const router = useRouter()
  useDocumentTitle(t('common.menus.leads'))

  const { isCurrentWorkspaceEditor } = useAppContext()

  // State
  const [activeTab, setActiveTab] = useState<string>('leads')

  // Handle tab change - navigate to sub-pages for new features
  const handleTabChange = (tab: string) => {
    if (tab === 'outreach') {
      router.push('/leads/outreach')
      return
    }
    if (tab === 'inbox') {
      router.push('/leads/inbox')
      return
    }
    if (tab === 'dashboard') {
      router.push('/leads/dashboard')
      return
    }
    setActiveTab(tab)
  }
  const [page, setPage] = useState(0)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [taskFilter, setTaskFilter] = useState<string>('')
  const [platformFilter, setPlatformFilter] = useState<string>('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null)
  const [taskToEdit, setTaskToEdit] = useState<LeadTask | null>(null)
  const [selectedTask, setSelectedTask] = useState<LeadTask | null>(null)
  const [hasRunningTasks, setHasRunningTasks] = useState(false)

  // Data fetching
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useLeadList({
    page: page + 1,
    limit: 20,
    keyword: searchKeyword || undefined,
    task_id: taskFilter || undefined,
    platform: platformFilter || undefined,
  })
  const { data: tasksData, isLoading: tasksLoading } = useLeadTaskList({
    page: 1,
    limit: 50,
  }, {
    // Auto-refresh every 3 seconds when there are running tasks
    refetchInterval: hasRunningTasks ? 3000 : false,
  })
  const { data: stats } = useLeadStats()

  // Update hasRunningTasks when tasksData changes
  useEffect(() => {
    const running = tasksData?.data?.some(t => t.status === 'running') ?? false
    setHasRunningTasks(running)
  }, [tasksData])

  // Mutations
  const createTask = useCreateLeadTask()
  const runTask = useRunLeadTask()
  const deleteTask = useDeleteLeadTask()
  const updateTask = useUpdateLeadTask()
  const restartTask = useRestartLeadTask()
  const updateLead = useUpdateLead()

  const tabs = [
    { value: 'leads', text: t('leads.tabs.leads') },
    { value: 'tasks', text: t('leads.tabs.tasks') },
    { value: 'outreach', text: t('leads.tabs.outreach') },
    { value: 'inbox', text: t('leads.tabs.inbox') },
    { value: 'dashboard', text: t('leads.tabs.dashboard') },
  ]

  const handleCreateTask = useCallback(async (data: CreateLeadTaskData) => {
    try {
      await createTask.mutateAsync(data)
      Toast.notify({ type: 'success', message: t('leads.message.taskCreated') })
      setShowCreateModal(false)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.createFailed') })
    }
  }, [createTask, t])

  const handleRunTask = useCallback(async (taskId: string) => {
    try {
      await runTask.mutateAsync(taskId)
      Toast.notify({ type: 'success', message: t('leads.message.taskStarted') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.startFailed') })
    }
  }, [runTask, t])

  const handleDeleteTask = useCallback(async () => {
    if (!taskToDelete)
      return
    try {
      await deleteTask.mutateAsync(taskToDelete)
      Toast.notify({ type: 'success', message: t('leads.message.taskDeleted') })
      setTaskToDelete(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.deleteFailed') })
    }
  }, [deleteTask, taskToDelete, t])

  const handleUpdateLeadStatus = useCallback(async (leadId: string, status: string) => {
    try {
      await updateLead.mutateAsync({ id: leadId, status })
      Toast.notify({ type: 'success', message: t('leads.message.leadUpdated') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.updateFailed') })
    }
  }, [updateLead, t])

  const handleEditTask = useCallback(async (data: UpdateLeadTaskData) => {
    if (!taskToEdit)
      return
    try {
      await updateTask.mutateAsync({ id: taskToEdit.id, ...data })
      Toast.notify({ type: 'success', message: t('leads.message.taskUpdated') })
      setShowEditModal(false)
      setTaskToEdit(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.updateFailed') })
    }
  }, [updateTask, taskToEdit, t])

  const handleRestartTask = useCallback(async (clearLeads: boolean) => {
    if (!selectedTask)
      return
    try {
      await restartTask.mutateAsync({ taskId: selectedTask.id, clearLeads })
      Toast.notify({ type: 'success', message: t('leads.message.taskRestarted') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.restartFailed') })
    }
  }, [restartTask, selectedTask, t])

  const openEditModal = useCallback((task: LeadTask) => {
    setTaskToEdit(task)
    setShowEditModal(true)
  }, [])

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      {/* Header */}
      <div className='sticky top-0 z-10 flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-7'>
        <div className='flex items-center gap-4'>
          <TabSliderNew
            value={activeTab}
            onChange={handleTabChange}
            options={tabs}
          />
          {/* Stats badges */}
          {stats && (
            <div className='flex items-center gap-2'>
              <span className='text-sm text-text-tertiary'>
                {t('leads.stats.total')}: <span className='font-medium text-text-secondary'>{stats.total}</span>
              </span>
              <span className='text-sm text-text-tertiary'>
                {t('leads.stats.highIntent')}: <span className='font-medium text-util-colors-green-green-600'>{stats.high_intent}</span>
              </span>
            </div>
          )}
        </div>
        <div className='flex items-center gap-2'>
          {activeTab === 'leads' && (
            <>
              <select
                value={taskFilter}
                onChange={(e) => {
                  setTaskFilter(e.target.value)
                  setPage(0)
                }}
                className='h-9 rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 text-sm text-text-secondary focus:border-components-input-border-active focus:outline-none'
              >
                <option value=''>{t('leads.filter.allTasks')}</option>
                {tasksData?.data?.map(task => (
                  <option key={task.id} value={task.id}>
                    {task.name}
                  </option>
                ))}
              </select>
              <select
                value={platformFilter}
                onChange={(e) => {
                  setPlatformFilter(e.target.value)
                  setPage(0)
                }}
                className='h-9 rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 text-sm text-text-secondary focus:border-components-input-border-active focus:outline-none'
              >
                <option value=''>{t('leads.filter.allPlatforms')}</option>
                <option value='douyin'>{t('leads.platform.douyin')}</option>
                <option value='xiaohongshu'>{t('leads.platform.xiaohongshu')}</option>
                <option value='kuaishou'>{t('leads.platform.kuaishou')}</option>
                <option value='bilibili'>{t('leads.platform.bilibili')}</option>
                <option value='weibo'>{t('leads.platform.weibo')}</option>
              </select>
              <Input
                showLeftIcon
                showClearIcon
                wrapperClassName='w-[200px]'
                value={searchKeyword}
                placeholder={t('leads.search.placeholder')}
                onChange={e => setSearchKeyword(e.target.value)}
                onClear={() => setSearchKeyword('')}
              />
              <Button
                variant='secondary'
                onClick={() => refetchLeads()}
              >
                <RiRefreshLine className='h-4 w-4' />
              </Button>
            </>
          )}
          {activeTab === 'tasks' && isCurrentWorkspaceEditor && (
            <Button
              variant='primary'
              onClick={() => setShowCreateModal(true)}
            >
              <RiAddLine className='mr-1 h-4 w-4' />
              {t('leads.createTask.title')}
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className='px-12 pb-6'>
        {activeTab === 'leads' && (
          <>
            {leadsLoading
              ? (
                <div className='flex h-[200px] items-center justify-center'>
                  <Loading type='area' />
                </div>
              )
              : (
                <>
                  <div className='overflow-x-auto rounded-xl border border-divider-subtle bg-components-panel-bg'>
                    <table className='w-full min-w-[1100px]'>
                      <thead>
                        <tr className='border-b border-divider-subtle'>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.nickname')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.comment')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.task.platform')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.videoUrl')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.region')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.intentScore')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.status')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.reply')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.dm')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.actions')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {leadsData?.data?.map((lead: Lead) => (
                          <tr key={lead.id} className='border-b border-divider-subtle last:border-0 hover:bg-background-default-hover'>
                            <td className='px-4 py-3 text-sm text-text-secondary'>{lead.nickname || '-'}</td>
                            <td className='max-w-[250px] truncate px-4 py-3 text-sm text-text-secondary' title={lead.comment_content || ''}>
                              {lead.comment_content || '-'}
                            </td>
                            <td className='px-4 py-3 text-sm text-text-tertiary'>
                              <span className='inline-flex items-center rounded-md bg-util-colors-blue-blue-50 px-2 py-1 text-xs font-medium text-util-colors-blue-blue-600'>
                                {t(`leads.platform.${lead.platform}`) || lead.platform}
                              </span>
                            </td>
                            <td className='max-w-[180px] truncate px-4 py-3 text-sm text-text-tertiary'>
                              {lead.source_video_url
                                ? (
                                  <a
                                    href={lead.source_video_url}
                                    target='_blank'
                                    rel='noopener noreferrer'
                                    className='text-util-colors-blue-blue-600 hover:underline'
                                    title={lead.source_video_url}
                                  >
                                    {lead.source_video_title || t('leads.lead.viewVideo')}
                                  </a>
                                )
                                : '-'}
                            </td>
                            <td className='px-4 py-3 text-sm text-text-tertiary'>{lead.region || '-'}</td>
                            <td className='px-4 py-3'>
                              <div className='flex items-center gap-2'>
                                <div className={`h-2 w-2 rounded-full ${lead.intent_score >= 70 ? 'bg-util-colors-green-green-500' : lead.intent_score >= 40 ? 'bg-util-colors-orange-orange-500' : 'bg-util-colors-gray-gray-500'}`} />
                                <span className={`text-sm ${getIntentColor(lead.intent_score)}`}>{lead.intent_score}</span>
                              </div>
                            </td>
                            <td className='px-4 py-3'>
                              <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusClassName(lead.status)}`}>
                                {t(`leads.status.${lead.status}`)}
                              </span>
                            </td>
                            <td className='px-4 py-3'>
                              {lead.reply_url
                                ? (
                                  <a
                                    href={lead.reply_url}
                                    target='_blank'
                                    rel='noopener noreferrer'
                                    className='inline-flex items-center gap-1 rounded-md bg-util-colors-green-green-50 px-2 py-1 text-xs font-medium text-util-colors-green-green-600 hover:bg-util-colors-green-green-100'
                                  >
                                    {lead.replied_at ? t('leads.lead.replied') : t('leads.lead.goReply')}
                                  </a>
                                )
                                : <span className='text-text-quaternary'>-</span>}
                            </td>
                            <td className='px-4 py-3'>
                              {lead.profile_url
                                ? (
                                  <a
                                    href={lead.profile_url}
                                    target='_blank'
                                    rel='noopener noreferrer'
                                    className='inline-flex items-center gap-1 rounded-md bg-util-colors-indigo-indigo-50 px-2 py-1 text-xs font-medium text-util-colors-indigo-indigo-600 hover:bg-util-colors-indigo-indigo-100'
                                  >
                                    {t('leads.lead.sendDM')}
                                  </a>
                                )
                                : <span className='text-text-quaternary'>-</span>}
                            </td>
                            <td className='px-4 py-3'>
                              <div className='flex items-center gap-1'>
                                {lead.status === 'new' && (
                                  <Button
                                    variant='ghost'
                                    size='small'
                                    onClick={() => handleUpdateLeadStatus(lead.id, 'contacted')}
                                  >
                                    {t('leads.lead.markContacted')}
                                  </Button>
                                )}
                                {lead.status === 'contacted' && (
                                  <Button
                                    variant='ghost'
                                    size='small'
                                    onClick={() => handleUpdateLeadStatus(lead.id, 'converted')}
                                  >
                                    {t('leads.lead.markConverted')}
                                  </Button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {(!leadsData?.data || leadsData.data.length === 0) && (
                      <div className='py-12 text-center'>
                        <p className='text-text-tertiary'>{t('leads.empty.leads')}</p>
                        <p className='mt-1 text-sm text-text-quaternary'>{t('leads.empty.leadsDescription')}</p>
                      </div>
                    )}
                  </div>

                  {leadsData && leadsData.total > 0 && (
                    <Pagination
                      className='mt-4'
                      current={page}
                      onChange={setPage}
                      total={leadsData.total}
                      limit={20}
                    />
                  )}
                </>
              )}
          </>
        )}

        {activeTab === 'tasks' && (
          <>
            {selectedTask
              ? (
                <TaskDetailView
                  task={selectedTask}
                  onBack={() => setSelectedTask(null)}
                  onEdit={() => openEditModal(selectedTask)}
                  onRestart={handleRestartTask}
                  isRestarting={restartTask.isPending}
                />
              )
              : tasksLoading
                ? (
                  <div className='flex h-[200px] items-center justify-center'>
                    <Loading type='area' />
                  </div>
                )
                : (
                  <div className='grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3'>
                    {tasksData?.data?.map((task: LeadTask) => (
                      <div
                        key={task.id}
                        className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4 transition-shadow hover:shadow-sm'
                      >
                        <div className='mb-3 flex items-center justify-between'>
                          <h3 className='font-medium text-text-secondary'>{task.name}</h3>
                          <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getTaskStatusClassName(task.status)}`}>
                            {t(`leads.taskStatus.${task.status}`)}
                          </span>
                        </div>
                        <div className='mb-2 text-sm text-text-tertiary'>
                          {t(`leads.taskType.${task.task_type}`)} · {task.platform}
                        </div>
                        <div className='mb-4 text-sm text-text-quaternary'>
                          {t('leads.task.totalLeads')}: {task.total_leads}
                        </div>
                        {task.error_message && (
                          <div className='mb-4 truncate text-sm text-util-colors-red-red-600' title={task.error_message}>
                            {task.error_message}
                          </div>
                        )}
                        <div className='flex flex-wrap gap-2'>
                          {(task.status === 'pending' || task.status === 'failed') && (
                            <Button
                              variant='primary'
                              size='small'
                              onClick={() => handleRunTask(task.id)}
                              loading={runTask.isPending}
                            >
                              <RiPlayLine className='mr-1 h-3 w-3' />
                              {t('leads.task.run')}
                            </Button>
                          )}
                          {task.status === 'running' && (
                            <Button
                              variant='secondary'
                              size='small'
                              disabled
                            >
                              <RiRefreshLine className='mr-1 h-3 w-3 animate-spin' />
                              {t('leads.taskStatus.running')}
                            </Button>
                          )}
                          {(task.status === 'completed' || task.status === 'failed') && (
                            <Button
                              variant='secondary'
                              size='small'
                              onClick={() => restartTask.mutate({ taskId: task.id, clearLeads: false })}
                              loading={restartTask.isPending}
                            >
                              <RiRestartLine className='mr-1 h-3 w-3' />
                              {t('leads.task.restart')}
                            </Button>
                          )}
                          <Button
                            variant='ghost'
                            size='small'
                            onClick={() => setSelectedTask(task)}
                            title={t('leads.task.viewDetails')}
                          >
                            <RiEyeLine className='h-3 w-3' />
                          </Button>
                          {task.status !== 'running' && (
                            <Button
                              variant='ghost'
                              size='small'
                              onClick={() => openEditModal(task)}
                              title={t('leads.task.edit')}
                            >
                              <RiEdit2Line className='h-3 w-3' />
                            </Button>
                          )}
                          <Button
                            variant='ghost'
                            size='small'
                            onClick={() => setTaskToDelete(task.id)}
                            title={t('common.operation.delete')}
                          >
                            <RiDeleteBinLine className='h-3 w-3' />
                          </Button>
                        </div>
                      </div>
                    ))}

                    {(!tasksData?.data || tasksData.data.length === 0) && (
                      <div className='col-span-full py-12 text-center'>
                        <p className='text-text-tertiary'>{t('leads.empty.tasks')}</p>
                        <p className='mt-1 text-sm text-text-quaternary'>{t('leads.empty.tasksDescription')}</p>
                      </div>
                    )}
                  </div>
                )}
          </>
        )}
      </div>

      {/* Create Task Modal */}
      <Modal
        isShow={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={t('leads.createTask.title')}
        className='!max-w-[480px]'
      >
        <TaskForm
          mode='create'
          onSubmit={handleCreateTask}
          onCancel={() => setShowCreateModal(false)}
          isLoading={createTask.isPending}
        />
      </Modal>

      {/* Edit Task Modal */}
      <Modal
        isShow={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setTaskToEdit(null)
        }}
        title={t('leads.editTask.title')}
        className='!max-w-[480px]'
      >
        {taskToEdit && (
          <TaskForm
            mode='edit'
            initialData={taskToEdit}
            onSubmit={handleEditTask}
            onCancel={() => {
              setShowEditModal(false)
              setTaskToEdit(null)
            }}
            isLoading={updateTask.isPending}
          />
        )}
      </Modal>

      {/* Delete Confirmation */}
      <Confirm
        isShow={!!taskToDelete}
        onCancel={() => setTaskToDelete(null)}
        onConfirm={handleDeleteTask}
        title={t('leads.confirm.deleteTask')}
        content={t('leads.confirm.deleteTaskDescription')}
        confirmText={t('common.operation.delete')}
        type='warning'
      />
    </div>
  )
}

export default LeadsPage
