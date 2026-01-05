'use client'
import type { FC } from 'react'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'next/navigation'
import {
  RiAddLine,
  RiDeleteBinLine,
  RiEditLine,
  RiPlayLine,
  RiRefreshLine,
  RiStopLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import Modal from '@/app/components/base/modal'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'
import Confirm from '@/app/components/base/confirm'
import Pagination from '@/app/components/base/pagination'
import LeadsNav from './components/leads-nav'
import {
  useCreateLeadTask,
  useDeleteLeadTask,
  useLeadList,
  useLeadPlatforms,
  useLeadTaskList,
  useRestartLeadTask,
  useRunLeadTask,
  useUpdateLead,
  useUpdateLeadTask,
} from '@/service/use-leads'
import type { Lead, LeadTask } from '@/service/use-leads'

// =============================================================================
// Task Form Component
// =============================================================================

type TaskFormProps = {
  onSubmit: (data: Partial<LeadTask>) => void
  onCancel: () => void
  isLoading: boolean
  initialData?: LeadTask
}

const TaskForm: FC<TaskFormProps> = ({ onSubmit, onCancel, isLoading, initialData }) => {
  const { t } = useTranslation()
  const { data: platformsData } = useLeadPlatforms()
  const [name, setName] = useState(initialData?.name || '')
  const [platform, setPlatform] = useState(initialData?.platform || 'douyin')
  const [videoUrls, setVideoUrls] = useState(initialData?.config?.video_urls?.join('\n') || '')
  const [keywords, setKeywords] = useState(initialData?.config?.keywords?.join(', ') || '')
  const [commentKeywords, setCommentKeywords] = useState(initialData?.config?.comment_keywords?.join(', ') || '')
  const [maxComments, setMaxComments] = useState(initialData?.config?.max_comments?.toString() || '100')

  const handleSubmit = () => {
    if (!name.trim()) {
      Toast.notify({ type: 'error', message: t('leads.task.nameRequired') })
      return
    }
    onSubmit({
      name: name.trim(),
      platform,
      config: {
        video_urls: videoUrls.split('\n').map(u => u.trim()).filter(Boolean),
        keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
        comment_keywords: commentKeywords.split(',').map(k => k.trim()).filter(Boolean),
        max_comments: parseInt(maxComments, 10) || 100,
      },
    })
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
          placeholder={t('leads.task.namePlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.task.platform')}
        </label>
        <select
          value={platform}
          onChange={e => setPlatform(e.target.value)}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          disabled={!!initialData}
        >
          {platformsData?.data?.map((p: { value: string; label: string }) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.task.videoUrls')}
        </label>
        <textarea
          value={videoUrls}
          onChange={e => setVideoUrls(e.target.value)}
          placeholder={t('leads.task.videoUrlsPlaceholder')}
          className='h-24 w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.task.keywords')}
        </label>
        <Input
          value={keywords}
          onChange={e => setKeywords(e.target.value)}
          placeholder={t('leads.task.keywordsPlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.task.commentKeywords')}
        </label>
        <Input
          value={commentKeywords}
          onChange={e => setCommentKeywords(e.target.value)}
          placeholder={t('leads.task.commentKeywordsPlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.task.maxComments')}
        </label>
        <Input
          type='number'
          value={maxComments}
          onChange={e => setMaxComments(e.target.value)}
          placeholder='100'
        />
      </div>
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>
          {t('common.operation.cancel')}
        </Button>
        <Button variant='primary' onClick={handleSubmit} loading={isLoading}>
          {initialData ? t('common.operation.save') : t('common.operation.create')}
        </Button>
      </div>
    </div>
  )
}

// =============================================================================
// Status Badge Component
// =============================================================================

const getStatusBadgeClass = (status: string): string => {
  const classes: Record<string, string> = {
    pending: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
    running: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    completed: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    failed: 'bg-util-colors-red-red-50 text-util-colors-red-red-600',
    new: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    contacted: 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600',
    converted: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    invalid: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
  }
  return classes[status] || 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600'
}

// =============================================================================
// Main Page Component
// =============================================================================

const LeadsPage: FC = () => {
  const { t } = useTranslation()
  const searchParams = useSearchParams()
  const currentTab = searchParams.get('tab') === 'tasks' ? 'tasks' : 'leads'

  useDocumentTitle(t('leads.title'))

  // State
  const [activeTab, setActiveTab] = useState<string>(currentTab)
  const [page, setPage] = useState(1)
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [taskToEdit, setTaskToEdit] = useState<LeadTask | null>(null)
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null)

  // Data
  const { data: tasksData, isLoading: tasksLoading, refetch: refetchTasks } = useLeadTaskList({ page, limit: 20 })
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useLeadList({ page, limit: 20 })

  // Mutations
  const createTask = useCreateLeadTask()
  const updateTask = useUpdateLeadTask()
  const deleteTask = useDeleteLeadTask()
  const runTask = useRunLeadTask()
  const restartTask = useRestartLeadTask()
  const updateLead = useUpdateLead()

  const tabs = [
    { value: 'leads', text: t('leads.tabs.leads') },
    { value: 'tasks', text: t('leads.tabs.tasks') },
  ]

  // Handlers
  const handleCreateTask = useCallback(async (data: Partial<LeadTask>) => {
    try {
      await createTask.mutateAsync(data)
      Toast.notify({ type: 'success', message: t('leads.message.taskCreated') })
      setShowCreateTask(false)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.createFailed') })
    }
  }, [createTask, t])

  const handleUpdateTask = useCallback(async (data: Partial<LeadTask>) => {
    if (!taskToEdit)
      return
    try {
      await updateTask.mutateAsync({ id: taskToEdit.id, ...data })
      Toast.notify({ type: 'success', message: t('leads.message.taskUpdated') })
      setTaskToEdit(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.updateFailed') })
    }
  }, [updateTask, taskToEdit, t])

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

  const handleRunTask = useCallback(async (taskId: string) => {
    try {
      await runTask.mutateAsync(taskId)
      Toast.notify({ type: 'success', message: t('leads.message.taskStarted') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.startFailed') })
    }
  }, [runTask, t])

  const handleRestartTask = useCallback(async (taskId: string) => {
    try {
      await restartTask.mutateAsync({ taskId, clearLeads: false })
      Toast.notify({ type: 'success', message: t('leads.message.taskRestarted') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.restartFailed') })
    }
  }, [restartTask, t])

  const handleUpdateLeadStatus = useCallback(async (leadId: string, status: string) => {
    try {
      await updateLead.mutateAsync({ id: leadId, status })
      Toast.notify({ type: 'success', message: t('leads.message.leadUpdated') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.message.updateFailed') })
    }
  }, [updateLead, t])

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      {/* Header */}
      <div className='flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-4'>
        <div className='flex items-center gap-4'>
          <TabSliderNew value={activeTab} onChange={setActiveTab} options={tabs} />
        </div>
        <div className='flex items-center gap-2'>
          {activeTab === 'tasks' && (
            <>
              <Button variant='secondary' onClick={() => refetchTasks()}>
                <RiRefreshLine className='h-4 w-4' />
              </Button>
              <Button variant='primary' onClick={() => setShowCreateTask(true)}>
                <RiAddLine className='mr-1 h-4 w-4' />
                {t('leads.task.create')}
              </Button>
            </>
          )}
          {activeTab === 'leads' && (
            <Button variant='secondary' onClick={() => refetchLeads()}>
              <RiRefreshLine className='h-4 w-4' />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className='px-12 pb-6'>
        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <>
            {tasksLoading
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
                      <div className='mb-3 flex items-start justify-between'>
                        <div>
                          <h3 className='font-medium text-text-secondary'>{task.name}</h3>
                          <p className='text-sm text-text-tertiary'>{task.platform}</p>
                        </div>
                        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusBadgeClass(task.status)}`}>
                          {t(`leads.status.${task.status}`)}
                        </span>
                      </div>
                      <div className='mb-3 text-sm text-text-tertiary'>
                        <span>{t('leads.task.totalLeads')}: {task.total_leads || 0}</span>
                      </div>
                      <div className='flex flex-wrap gap-2'>
                        {task.status === 'pending' && (
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
                        {(task.status === 'completed' || task.status === 'failed') && (
                          <Button
                            variant='primary'
                            size='small'
                            onClick={() => handleRestartTask(task.id)}
                            loading={restartTask.isPending}
                          >
                            <RiRefreshLine className='mr-1 h-3 w-3' />
                            {t('leads.task.restart')}
                          </Button>
                        )}
                        {task.status === 'running' && (
                          <Button variant='secondary' size='small' disabled>
                            <RiStopLine className='mr-1 h-3 w-3' />
                            {t('leads.task.running')}
                          </Button>
                        )}
                        <Button
                          variant='secondary'
                          size='small'
                          onClick={() => setTaskToEdit(task)}
                        >
                          <RiEditLine className='h-3 w-3' />
                        </Button>
                        <Button
                          variant='ghost'
                          size='small'
                          onClick={() => setTaskToDelete(task.id)}
                        >
                          <RiDeleteBinLine className='h-3 w-3' />
                        </Button>
                      </div>
                    </div>
                  ))}
                  {(!tasksData?.data || tasksData.data.length === 0) && (
                    <div className='col-span-full py-12 text-center'>
                      <p className='text-text-tertiary'>{t('leads.empty.tasks')}</p>
                    </div>
                  )}
                </div>
              )}
            {tasksData && tasksData.total > 20 && (
              <Pagination
                className='mt-4'
                current={page - 1}
                onChange={p => setPage(p + 1)}
                total={tasksData.total}
                limit={20}
              />
            )}
          </>
        )}

        {/* Leads Tab */}
        {activeTab === 'leads' && (
          <>
            {leadsLoading
              ? (
                <div className='flex h-[200px] items-center justify-center'>
                  <Loading type='area' />
                </div>
              )
              : (
                <div className='overflow-x-auto rounded-xl border border-divider-subtle bg-components-panel-bg'>
                  <table className='w-full'>
                    <thead>
                      <tr className='border-b border-divider-subtle'>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.nickname')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.platform')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.comment')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.intentScore')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.status')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.actions')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leadsData?.data?.map((lead: Lead) => (
                        <tr key={lead.id} className='border-b border-divider-subtle last:border-0'>
                          <td className='px-4 py-3 text-sm text-text-secondary'>{lead.nickname}</td>
                          <td className='px-4 py-3'>
                            <span className='inline-flex items-center rounded-md bg-util-colors-blue-blue-50 px-2 py-1 text-xs text-util-colors-blue-blue-600'>
                              {lead.platform}
                            </span>
                          </td>
                          <td className='max-w-[300px] truncate px-4 py-3 text-sm text-text-tertiary'>
                            {lead.comment_content}
                          </td>
                          <td className='px-4 py-3'>
                            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${lead.intent_score >= 70 ? 'bg-util-colors-green-green-50 text-util-colors-green-green-600' : lead.intent_score >= 40 ? 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600' : 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600'}`}>
                              {lead.intent_score}
                            </span>
                          </td>
                          <td className='px-4 py-3'>
                            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusBadgeClass(lead.status)}`}>
                              {t(`leads.leadStatus.${lead.status}`)}
                            </span>
                          </td>
                          <td className='px-4 py-3'>
                            <select
                              value={lead.status}
                              onChange={e => handleUpdateLeadStatus(lead.id, e.target.value)}
                              className='rounded-md border border-components-input-border-active bg-components-input-bg-normal px-2 py-1 text-xs text-text-secondary'
                            >
                              <option value='new'>{t('leads.leadStatus.new')}</option>
                              <option value='contacted'>{t('leads.leadStatus.contacted')}</option>
                              <option value='converted'>{t('leads.leadStatus.converted')}</option>
                              <option value='invalid'>{t('leads.leadStatus.invalid')}</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {(!leadsData?.data || leadsData.data.length === 0) && (
                    <div className='py-12 text-center'>
                      <p className='text-text-tertiary'>{t('leads.empty.leads')}</p>
                    </div>
                  )}
                </div>
              )}
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

      {/* Modals */}
      <Modal isShow={showCreateTask} onClose={() => setShowCreateTask(false)} title={t('leads.task.create')} className='!max-w-[480px]'>
        <TaskForm
          onSubmit={handleCreateTask}
          onCancel={() => setShowCreateTask(false)}
          isLoading={createTask.isPending}
        />
      </Modal>

      <Modal isShow={!!taskToEdit} onClose={() => setTaskToEdit(null)} title={t('leads.task.edit')} className='!max-w-[480px]'>
        {taskToEdit && (
          <TaskForm
            onSubmit={handleUpdateTask}
            onCancel={() => setTaskToEdit(null)}
            isLoading={updateTask.isPending}
            initialData={taskToEdit}
          />
        )}
      </Modal>

      <Confirm
        isShow={!!taskToDelete}
        onCancel={() => setTaskToDelete(null)}
        onConfirm={handleDeleteTask}
        title={t('leads.confirm.deleteTask')}
        content={t('leads.confirm.deleteTaskDesc')}
        type='warning'
      />
    </div>
  )
}

export default LeadsPage
