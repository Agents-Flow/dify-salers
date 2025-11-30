/**
 * Leads Page - Lead acquisition management
 * Following Dify's Apps list page pattern
 * Reference: web/app/components/apps/list.tsx
 */
'use client'
import type { FC } from 'react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiAddLine,
  RiDeleteBinLine,
  RiPlayLine,
  RiRefreshLine,
} from '@remixicon/react'
import {
  getIntentColor,
  useCreateLeadTask,
  useDeleteLeadTask,
  useLeadList,
  useLeadStats,
  useLeadTaskList,
  useRunLeadTask,
  useUpdateLead,
} from '@/service/use-leads'
import type { CreateLeadTaskData, Lead, LeadTask } from '@/service/use-leads'
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

// Create Task Form Component
type CreateTaskFormProps = {
  onSubmit: (data: CreateLeadTaskData) => void
  onCancel: () => void
  isLoading: boolean
}

const CreateTaskForm: FC<CreateTaskFormProps> = ({ onSubmit, onCancel, isLoading }) => {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [videoUrl, setVideoUrl] = useState('')
  const [keywords, setKeywords] = useState('')
  const [city, setCity] = useState('')

  const handleSubmit = () => {
    if (!name.trim()) {
      Toast.notify({ type: 'error', message: t('leads.createTask.nameRequired') })
      return
    }

    const videoUrls = videoUrl.trim() ? [videoUrl.trim()] : []
    const keywordList = keywords.trim() ? keywords.split(',').map(k => k.trim()).filter(Boolean) : []

    onSubmit({
      name: name.trim(),
      task_type: 'comment_crawl',
      config: {
        video_urls: videoUrls,
        keywords: keywordList,
        city: city.trim() || undefined,
        max_comments: 500,
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
          placeholder={t('leads.createTask.namePlaceholder')}
        />
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
          {t('leads.createTask.submit')}
        </Button>
      </div>
    </div>
  )
}

const LeadsPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('common.menus.leads'))

  const { isCurrentWorkspaceEditor } = useAppContext()

  // State
  const [activeTab, setActiveTab] = useState<string>('leads')
  const [page, setPage] = useState(0)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null)
  const [hasRunningTasks, setHasRunningTasks] = useState(false)

  // Data fetching
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useLeadList({
    page: page + 1,
    limit: 20,
    keyword: searchKeyword || undefined,
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
  const updateLead = useUpdateLead()

  const tabs = [
    { value: 'leads', text: t('leads.tabs.leads') },
    { value: 'tasks', text: t('leads.tabs.tasks') },
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

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      {/* Header */}
      <div className='sticky top-0 z-10 flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-7'>
        <div className='flex items-center gap-4'>
          <TabSliderNew
            value={activeTab}
            onChange={setActiveTab}
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
                  <div className='rounded-xl border border-divider-subtle bg-components-panel-bg'>
                    <table className='w-full'>
                      <thead>
                        <tr className='border-b border-divider-subtle'>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.nickname')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.comment')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.source')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.intentScore')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.status')}</th>
                          <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.lead.actions')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {leadsData?.data?.map((lead: Lead) => (
                          <tr key={lead.id} className='border-b border-divider-subtle last:border-0 hover:bg-background-default-hover'>
                            <td className='px-4 py-3 text-sm text-text-secondary'>{lead.nickname || '-'}</td>
                            <td className='max-w-[300px] truncate px-4 py-3 text-sm text-text-secondary' title={lead.comment_content || ''}>
                              {lead.comment_content || '-'}
                            </td>
                            <td className='max-w-[200px] truncate px-4 py-3 text-sm text-text-tertiary' title={lead.source_video_title || ''}>
                              {lead.source_video_title || '-'}
                            </td>
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
                        <div className='mb-4 text-sm text-util-colors-red-red-600'>
                          {task.error_message}
                        </div>
                      )}
                      <div className='flex gap-2'>
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
        <CreateTaskForm
          onSubmit={handleCreateTask}
          onCancel={() => setShowCreateModal(false)}
          isLoading={createTask.isPending}
        />
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
