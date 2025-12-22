'use client'
import type { FC } from 'react'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiAddLine,
  RiCheckLine,
  RiCloseLine,
  RiComputerLine,
  RiDeleteBinLine,
  RiErrorWarningLine,
  RiLoader2Line,
  RiPlayLine,
  RiRefreshLine,
  RiServerLine,
  RiTimeLine,
  RiUser3Line,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import Modal from '@/app/components/base/modal'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'
import Confirm from '@/app/components/base/confirm'
import {
  getSessionStatusColor,
  useAutomationMonitor,
  useAutomationSessionStats,
  useAutomationSessions,
  useBrowserPoolStatus,
  useCreateAutomationSession,
  useDeleteAutomationSession,
  useExecuteAutomation,
} from '@/service/use-leads'
import type {
  AutomationSession,
  AutomationSessionStatus,
  CreateSessionRequest,
} from '@/service/use-leads'

// =============================================================================
// Session Login Form
// =============================================================================

type LoginFormProps = {
  onSubmit: (data: CreateSessionRequest) => void
  onCancel: () => void
  isLoading: boolean
}

const LoginForm: FC<LoginFormProps> = ({ onSubmit, onCancel, isLoading }) => {
  const { t } = useTranslation()
  const [platform, setPlatform] = useState<'instagram' | 'twitter'>('instagram')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [proxy, setProxy] = useState('')

  const handleSubmit = () => {
    if (!username.trim() || !password.trim()) {
      Toast.notify({ type: 'error', message: t('leads.automation.sessions.usernamePasswordRequired') })
      return
    }
    if (platform === 'twitter' && !email.trim()) {
      Toast.notify({ type: 'error', message: t('leads.automation.sessions.emailRequired') })
      return
    }
    onSubmit({
      platform,
      username: username.trim(),
      password: password.trim(),
      email: platform === 'twitter' ? email.trim() : undefined,
      proxy: proxy.trim() || undefined,
    })
  }

  return (
    <div className='space-y-4 p-6'>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.sessions.platform')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <select
          value={platform}
          onChange={e => setPlatform(e.target.value as 'instagram' | 'twitter')}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value='instagram'>Instagram</option>
          <option value='twitter'>X (Twitter)</option>
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.sessions.username')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <Input
          value={username}
          onChange={e => setUsername(e.target.value)}
          placeholder='@username'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.sessions.password')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <Input
          type='password'
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder='••••••••'
        />
      </div>
      {platform === 'twitter' && (
        <div>
          <label className='mb-1 block text-sm font-medium text-text-secondary'>
            {t('leads.automation.sessions.email')} <span className='text-util-colors-red-red-600'>*</span>
          </label>
          <Input
            type='email'
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder='email@example.com'
          />
        </div>
      )}
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.sessions.proxy')}
        </label>
        <Input
          value={proxy}
          onChange={e => setProxy(e.target.value)}
          placeholder='socks5://user:pass@host:port'
        />
        <p className='mt-1 text-xs text-text-tertiary'>{t('leads.automation.sessions.proxyHelp')}</p>
      </div>
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>
          {t('common.operation.cancel')}
        </Button>
        <Button variant='primary' onClick={handleSubmit} loading={isLoading}>
          {t('leads.automation.sessions.login')}
        </Button>
      </div>
    </div>
  )
}

// =============================================================================
// Execute Action Form
// =============================================================================

type ExecuteFormProps = {
  sessions: AutomationSession[]
  onCancel: () => void
}

const ExecuteForm: FC<ExecuteFormProps> = ({ sessions, onCancel }) => {
  const { t } = useTranslation()
  const executeAction = useExecuteAutomation()
  const [actionType, setActionType] = useState<'follow' | 'dm'>('follow')
  const [accountUsername, setAccountUsername] = useState('')
  const [targetUsername, setTargetUsername] = useState('')
  const [message, setMessage] = useState('')

  const handleSubmit = async () => {
    if (!accountUsername) {
      Toast.notify({ type: 'error', message: t('leads.automation.execute.selectAccount') })
      return
    }
    if (!targetUsername.trim()) {
      Toast.notify({ type: 'error', message: t('leads.automation.execute.targetRequired') })
      return
    }
    if (actionType === 'dm' && !message.trim()) {
      Toast.notify({ type: 'error', message: t('leads.automation.execute.messageRequired') })
      return
    }

    const selectedSession = sessions.find(s => s.username === accountUsername)
    if (!selectedSession) {
      Toast.notify({ type: 'error', message: t('leads.automation.execute.sessionNotFound') })
      return
    }

    try {
      const result = await executeAction.mutateAsync({
        action_type: actionType,
        platform: selectedSession.platform,
        account_username: accountUsername,
        target_username: targetUsername.trim().replace('@', ''),
        message: actionType === 'dm' ? message.trim() : undefined,
      })
      if (result.success) {
        Toast.notify({ type: 'success', message: t('leads.automation.execute.success') })
        onCancel()
      }
      else {
        Toast.notify({ type: 'error', message: result.error || t('leads.automation.execute.failed') })
      }
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.automation.execute.failed') })
    }
  }

  return (
    <div className='space-y-4 p-6'>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.execute.actionType')}
        </label>
        <select
          value={actionType}
          onChange={e => setActionType(e.target.value as 'follow' | 'dm')}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value='follow'>{t('leads.automation.execute.follow')}</option>
          <option value='dm'>{t('leads.automation.execute.dm')}</option>
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.execute.account')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <select
          value={accountUsername}
          onChange={e => setAccountUsername(e.target.value)}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value=''>{t('leads.automation.execute.selectAccount')}</option>
          {sessions.filter(s => s.status === 'active').map(s => (
            <option key={`${s.platform}-${s.username}`} value={s.username}>
              @{s.username} ({s.platform})
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.automation.execute.target')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <Input
          value={targetUsername}
          onChange={e => setTargetUsername(e.target.value)}
          placeholder='@target_username'
        />
      </div>
      {actionType === 'dm' && (
        <div>
          <label className='mb-1 block text-sm font-medium text-text-secondary'>
            {t('leads.automation.execute.message')} <span className='text-util-colors-red-red-600'>*</span>
          </label>
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            placeholder={t('leads.automation.execute.messagePlaceholder')}
            className='h-24 w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          />
        </div>
      )}
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>
          {t('common.operation.cancel')}
        </Button>
        <Button variant='primary' onClick={handleSubmit} loading={executeAction.isPending}>
          <RiPlayLine className='mr-1 h-4 w-4' />
          {t('leads.automation.execute.run')}
        </Button>
      </div>
    </div>
  )
}

// =============================================================================
// Sessions Tab
// =============================================================================

const SessionsTab: FC = () => {
  const { t } = useTranslation()
  const [showLogin, setShowLogin] = useState(false)
  const [showExecute, setShowExecute] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<{ platform: string; username: string } | null>(null)

  const { data: sessionsData, isLoading, refetch } = useAutomationSessions()
  const { data: statsData } = useAutomationSessionStats()
  const createSession = useCreateAutomationSession()
  const deleteSession = useDeleteAutomationSession()

  const handleLogin = useCallback(async (data: CreateSessionRequest) => {
    try {
      const result = await createSession.mutateAsync(data)
      if (result.success) {
        Toast.notify({ type: 'success', message: t('leads.automation.sessions.loginSuccess') })
        setShowLogin(false)
      }
      else {
        Toast.notify({ type: 'error', message: result.error || t('leads.automation.sessions.loginFailed') })
      }
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.automation.sessions.loginFailed') })
    }
  }, [createSession, t])

  const handleDelete = useCallback(async () => {
    if (!sessionToDelete)
      return
    try {
      await deleteSession.mutateAsync(sessionToDelete)
      Toast.notify({ type: 'success', message: t('leads.automation.sessions.logoutSuccess') })
      setSessionToDelete(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.automation.sessions.logoutFailed') })
    }
  }, [deleteSession, sessionToDelete, t])

  return (
    <div className='space-y-6'>
      {/* Stats Cards */}
      {statsData && (
        <div className='grid grid-cols-2 gap-4 md:grid-cols-4'>
          <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
            <div className='text-2xl font-semibold text-text-secondary'>{statsData.total}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.sessions.totalSessions')}</div>
          </div>
          <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
            <div className='text-2xl font-semibold text-util-colors-green-green-600'>{statsData.active}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.sessions.activeSessions')}</div>
          </div>
          <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
            <div className='text-2xl font-semibold text-util-colors-orange-orange-600'>{statsData.rate_limited}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.sessions.rateLimited')}</div>
          </div>
          <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
            <div className='text-2xl font-semibold text-util-colors-red-red-600'>{statsData.banned}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.sessions.banned')}</div>
          </div>
        </div>
      )}

      {/* Sessions Table */}
      {isLoading
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
                  <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.automation.sessions.username')}</th>
                  <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.automation.sessions.platform')}</th>
                  <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.automation.sessions.status')}</th>
                  <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.automation.sessions.lastAction')}</th>
                  <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.automation.sessions.errors')}</th>
                  <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.automation.sessions.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {sessionsData?.data?.map((session: AutomationSession) => (
                  <tr key={`${session.platform}-${session.username}`} className='border-b border-divider-subtle last:border-0'>
                    <td className='px-4 py-3 text-sm text-text-secondary'>
                      <div className='flex items-center gap-2'>
                        <RiUser3Line className='h-4 w-4 text-text-tertiary' />
                        @{session.username}
                      </div>
                    </td>
                    <td className='px-4 py-3'>
                      <span className='inline-flex items-center rounded-md bg-util-colors-blue-blue-50 px-2 py-1 text-xs text-util-colors-blue-blue-600'>
                        {session.platform === 'twitter' ? 'X' : 'Instagram'}
                      </span>
                    </td>
                    <td className='px-4 py-3'>
                      <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getSessionStatusColor(session.status as AutomationSessionStatus)}`}>
                        {session.status === 'active' && <RiCheckLine className='mr-1 h-3 w-3' />}
                        {session.status === 'rate_limited' && <RiTimeLine className='mr-1 h-3 w-3' />}
                        {session.status === 'banned' && <RiCloseLine className='mr-1 h-3 w-3' />}
                        {t(`leads.automation.sessions.statusLabel.${session.status}`)}
                      </span>
                    </td>
                    <td className='px-4 py-3 text-sm text-text-tertiary'>
                      {session.last_action_at
                        ? new Date(session.last_action_at).toLocaleString()
                        : '-'}
                    </td>
                    <td className='px-4 py-3 text-sm text-text-tertiary'>
                      {session.error_count}
                    </td>
                    <td className='px-4 py-3'>
                      <Button
                        variant='ghost'
                        size='small'
                        onClick={() => setSessionToDelete({ platform: session.platform, username: session.username })}
                      >
                        <RiDeleteBinLine className='h-3 w-3' />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(!sessionsData?.data || sessionsData.data.length === 0) && (
              <div className='py-12 text-center'>
                <RiUser3Line className='mx-auto mb-2 h-8 w-8 text-text-quaternary' />
                <p className='text-text-tertiary'>{t('leads.automation.sessions.empty')}</p>
                <p className='mt-1 text-xs text-text-quaternary'>{t('leads.automation.sessions.emptyDesc')}</p>
              </div>
            )}
          </div>
        )}

      {/* Action Buttons */}
      <div className='flex gap-2'>
        <Button variant='primary' onClick={() => setShowLogin(true)}>
          <RiAddLine className='mr-1 h-4 w-4' />
          {t('leads.automation.sessions.addSession')}
        </Button>
        <Button variant='secondary' onClick={() => setShowExecute(true)} disabled={!sessionsData?.data?.length}>
          <RiPlayLine className='mr-1 h-4 w-4' />
          {t('leads.automation.sessions.testAction')}
        </Button>
        <Button variant='secondary' onClick={() => refetch()}>
          <RiRefreshLine className='h-4 w-4' />
        </Button>
      </div>

      {/* Modals */}
      <Modal isShow={showLogin} onClose={() => setShowLogin(false)} title={t('leads.automation.sessions.loginTitle')} className='!max-w-[480px]'>
        <LoginForm
          onSubmit={handleLogin}
          onCancel={() => setShowLogin(false)}
          isLoading={createSession.isPending}
        />
      </Modal>

      <Modal isShow={showExecute} onClose={() => setShowExecute(false)} title={t('leads.automation.execute.title')} className='!max-w-[480px]'>
        <ExecuteForm
          sessions={sessionsData?.data || []}
          onCancel={() => setShowExecute(false)}
        />
      </Modal>

      <Confirm
        isShow={!!sessionToDelete}
        onCancel={() => setSessionToDelete(null)}
        onConfirm={handleDelete}
        title={t('leads.automation.sessions.logoutConfirm')}
        content={t('leads.automation.sessions.logoutConfirmDesc')}
        type='warning'
      />
    </div>
  )
}

// =============================================================================
// Browser Pool Tab
// =============================================================================

const BrowserPoolTab: FC = () => {
  const { t } = useTranslation()
  const { data: poolStatus, isLoading, refetch } = useBrowserPoolStatus()

  const getInstanceStatusIcon = (status: string) => {
    switch (status) {
      case 'idle':
        return <RiCheckLine className='h-4 w-4 text-util-colors-green-green-600' />
      case 'busy':
        return <RiLoader2Line className='h-4 w-4 animate-spin text-util-colors-blue-blue-600' />
      case 'error':
        return <RiErrorWarningLine className='h-4 w-4 text-util-colors-red-red-600' />
      default:
        return <RiTimeLine className='h-4 w-4 text-text-tertiary' />
    }
  }

  if (isLoading) {
    return (
      <div className='flex h-[200px] items-center justify-center'>
        <Loading type='area' />
      </div>
    )
  }

  return (
    <div className='space-y-6'>
      {/* Pool Status Summary */}
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-6'>
        <div className='mb-4 flex items-center justify-between'>
          <h3 className='text-lg font-medium text-text-secondary'>{t('leads.automation.pool.title')}</h3>
          <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${poolStatus?.started ? 'bg-util-colors-green-green-50 text-util-colors-green-green-600' : 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600'}`}>
            {poolStatus?.started ? t('leads.automation.pool.running') : t('leads.automation.pool.stopped')}
          </span>
        </div>
        <div className='grid grid-cols-2 gap-4 md:grid-cols-5'>
          <div>
            <div className='text-2xl font-semibold text-text-secondary'>{poolStatus?.pool_size || 0}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.pool.poolSize')}</div>
          </div>
          <div>
            <div className='text-2xl font-semibold text-util-colors-green-green-600'>{poolStatus?.idle || 0}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.pool.idle')}</div>
          </div>
          <div>
            <div className='text-2xl font-semibold text-util-colors-blue-blue-600'>{poolStatus?.busy || 0}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.pool.busy')}</div>
          </div>
          <div>
            <div className='text-2xl font-semibold text-util-colors-red-red-600'>{poolStatus?.error || 0}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.pool.error')}</div>
          </div>
          <div>
            <div className='text-2xl font-semibold text-text-secondary'>{poolStatus?.total_instances || 0}</div>
            <div className='text-sm text-text-tertiary'>{t('leads.automation.pool.totalInstances')}</div>
          </div>
        </div>
      </div>

      {/* Instance List */}
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg'>
        <div className='border-b border-divider-subtle px-4 py-3'>
          <h4 className='text-sm font-medium text-text-secondary'>{t('leads.automation.pool.instances')}</h4>
        </div>
        <div className='divide-y divide-divider-subtle'>
          {poolStatus?.instances?.map(instance => (
            <div key={instance.id} className='flex items-center justify-between px-4 py-3'>
              <div className='flex items-center gap-3'>
                <RiComputerLine className='h-5 w-5 text-text-tertiary' />
                <div>
                  <div className='text-sm font-medium text-text-secondary'>{instance.id}</div>
                  <div className='text-xs text-text-tertiary'>
                    {t('leads.automation.pool.useCount')}: {instance.use_count}
                  </div>
                </div>
              </div>
              <div className='flex items-center gap-2'>
                {getInstanceStatusIcon(instance.status)}
                <span className='text-sm text-text-tertiary'>{instance.status}</span>
              </div>
            </div>
          ))}
          {(!poolStatus?.instances || poolStatus.instances.length === 0) && (
            <div className='px-4 py-8 text-center'>
              <RiServerLine className='mx-auto mb-2 h-8 w-8 text-text-quaternary' />
              <p className='text-sm text-text-tertiary'>{t('leads.automation.pool.noInstances')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Info Box */}
      <div className='rounded-xl border border-util-colors-blue-blue-200 bg-util-colors-blue-blue-50 p-4'>
        <h4 className='mb-2 text-sm font-medium text-util-colors-blue-blue-600'>{t('leads.automation.pool.infoTitle')}</h4>
        <p className='text-sm text-util-colors-blue-blue-600'>{t('leads.automation.pool.infoDesc')}</p>
      </div>

      <Button variant='secondary' onClick={() => refetch()}>
        <RiRefreshLine className='mr-1 h-4 w-4' />
        {t('common.operation.refresh')}
      </Button>
    </div>
  )
}

// =============================================================================
// Monitor Tab
// =============================================================================

const MonitorTab: FC = () => {
  const { t } = useTranslation()
  const { data: monitorData, isLoading, refetch } = useAutomationMonitor({ refetchInterval: 5000 })

  if (isLoading) {
    return (
      <div className='flex h-[200px] items-center justify-center'>
        <Loading type='area' />
      </div>
    )
  }

  return (
    <div className='space-y-6'>
      {/* Capacity Gauge */}
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-6'>
        <h3 className='mb-4 text-lg font-medium text-text-secondary'>{t('leads.automation.monitor.capacity')}</h3>
        <div className='mb-4'>
          <div className='mb-2 flex justify-between text-sm'>
            <span className='text-text-tertiary'>{t('leads.automation.monitor.utilization')}</span>
            <span className='font-medium text-text-secondary'>{monitorData?.capacity.utilization_percent}%</span>
          </div>
          <div className='bg-components-progress-track h-4 overflow-hidden rounded-full'>
            <div
              className='h-full rounded-full bg-util-colors-blue-blue-500 transition-all duration-300'
              style={{ width: `${monitorData?.capacity.utilization_percent || 0}%` }}
            />
          </div>
          <div className='mt-2 flex justify-between text-xs text-text-tertiary'>
            <span>{monitorData?.capacity.current_sessions || 0} {t('leads.automation.monitor.current')}</span>
            <span>{monitorData?.capacity.max_concurrent_sessions || 1000} {t('leads.automation.monitor.max')}</span>
          </div>
        </div>
      </div>

      {/* Memory Estimate */}
      <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
        <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
          <div className='text-2xl font-semibold text-text-secondary'>{monitorData?.memory_estimate.http_api_mb || 0} MB</div>
          <div className='text-sm text-text-tertiary'>{t('leads.automation.monitor.httpApiMemory')}</div>
        </div>
        <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
          <div className='text-2xl font-semibold text-text-secondary'>{monitorData?.memory_estimate.browser_pool_mb || 0} MB</div>
          <div className='text-sm text-text-tertiary'>{t('leads.automation.monitor.browserPoolMemory')}</div>
        </div>
        <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
          <div className='text-2xl font-semibold text-util-colors-blue-blue-600'>{monitorData?.memory_estimate.total_mb || 0} MB</div>
          <div className='text-sm text-text-tertiary'>{t('leads.automation.monitor.totalMemory')}</div>
        </div>
      </div>

      {/* Health Status */}
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-6'>
        <h3 className='mb-4 text-lg font-medium text-text-secondary'>{t('leads.automation.monitor.health')}</h3>
        <div className='grid grid-cols-2 gap-4 md:grid-cols-4'>
          <div className='flex items-center gap-3 rounded-lg bg-util-colors-green-green-50 p-3'>
            <RiCheckLine className='h-6 w-6 text-util-colors-green-green-600' />
            <div>
              <div className='text-xl font-semibold text-util-colors-green-green-600'>{monitorData?.health.active || 0}</div>
              <div className='text-xs text-util-colors-green-green-600'>{t('leads.automation.monitor.active')}</div>
            </div>
          </div>
          <div className='flex items-center gap-3 rounded-lg bg-util-colors-orange-orange-50 p-3'>
            <RiTimeLine className='h-6 w-6 text-util-colors-orange-orange-600' />
            <div>
              <div className='text-xl font-semibold text-util-colors-orange-orange-600'>{monitorData?.health.rate_limited || 0}</div>
              <div className='text-xs text-util-colors-orange-orange-600'>{t('leads.automation.monitor.rateLimited')}</div>
            </div>
          </div>
          <div className='flex items-center gap-3 rounded-lg bg-util-colors-blue-blue-50 p-3'>
            <RiErrorWarningLine className='h-6 w-6 text-util-colors-blue-blue-600' />
            <div>
              <div className='text-xl font-semibold text-util-colors-blue-blue-600'>{monitorData?.health.challenge_required || 0}</div>
              <div className='text-xs text-util-colors-blue-blue-600'>{t('leads.automation.monitor.challenge')}</div>
            </div>
          </div>
          <div className='flex items-center gap-3 rounded-lg bg-util-colors-red-red-50 p-3'>
            <RiCloseLine className='h-6 w-6 text-util-colors-red-red-600' />
            <div>
              <div className='text-xl font-semibold text-util-colors-red-red-600'>{monitorData?.health.banned || 0}</div>
              <div className='text-xs text-util-colors-red-red-600'>{t('leads.automation.monitor.banned')}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Architecture Info */}
      <div className='rounded-xl border border-util-colors-green-green-200 bg-util-colors-green-green-50 p-4'>
        <h4 className='mb-2 text-sm font-medium text-util-colors-green-green-600'>{t('leads.automation.monitor.archTitle')}</h4>
        <p className='text-sm text-util-colors-green-green-600'>{t('leads.automation.monitor.archDesc')}</p>
      </div>

      <Button variant='secondary' onClick={() => refetch()}>
        <RiRefreshLine className='mr-1 h-4 w-4' />
        {t('common.operation.refresh')}
      </Button>
    </div>
  )
}

// =============================================================================
// Main Page
// =============================================================================

const AutomationPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.automation.title'))

  const [activeTab, setActiveTab] = useState<string>('sessions')

  const tabs = [
    { value: 'sessions', text: t('leads.automation.tabs.sessions') },
    { value: 'pool', text: t('leads.automation.tabs.pool') },
    { value: 'monitor', text: t('leads.automation.tabs.monitor') },
  ]

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      {/* Header */}
      <div className='sticky top-0 z-10 flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-7'>
        <div>
          <h1 className='text-xl font-semibold text-text-primary'>{t('leads.automation.title')}</h1>
          <p className='mt-1 text-sm text-text-tertiary'>{t('leads.automation.description')}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className='px-12 pb-4'>
        <TabSliderNew value={activeTab} onChange={setActiveTab} options={tabs} />
      </div>

      {/* Content */}
      <div className='px-12 pb-6'>
        {activeTab === 'sessions' && <SessionsTab />}
        {activeTab === 'pool' && <BrowserPoolTab />}
        {activeTab === 'monitor' && <MonitorTab />}
      </div>
    </div>
  )
}

export default AutomationPage
