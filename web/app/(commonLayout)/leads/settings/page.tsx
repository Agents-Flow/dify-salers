'use client'
import type { FC } from 'react'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from 'next/navigation'
import {
  RiArrowLeftLine,
  RiCheckLine,
  RiKeyLine,
  RiLink,
  RiNotification3Line,
  RiServerLine,
  RiSettings3Line,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'
import { useLeadsConfigs, useTestConnection, useUpdateLeadsConfig } from '@/service/use-leads-settings'

// =============================================================================
// Types
// =============================================================================

type ConfigsType = Record<string, Record<string, unknown>>

// =============================================================================
// Config Section Component
// =============================================================================

type ConfigFieldProps = {
  label: string
  description?: string
  type: 'text' | 'password' | 'email' | 'url' | 'number' | 'boolean' | 'select' | 'textarea'
  value: string | boolean | number
  onChange: (value: string | boolean | number) => void
  options?: string[]
  placeholder?: string
  required?: boolean
}

const ConfigField: FC<ConfigFieldProps> = ({
  label,
  description,
  type,
  value,
  onChange,
  options,
  placeholder,
  required,
}) => {
  if (type === 'boolean') {
    return (
      <div className='flex items-center justify-between py-2'>
        <div>
          <div className='text-sm font-medium text-text-secondary'>{label}</div>
          {description && <div className='text-xs text-text-tertiary'>{description}</div>}
        </div>
        <button
          type='button'
          onClick={() => onChange(!value)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-util-colors-blue-blue-500' : 'bg-components-toggle-bg'}`}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white transition-transform${value ? 'translate-x-6' : 'translate-x-1'}`}
          />
        </button>
      </div>
    )
  }

  if (type === 'select') {
    return (
      <div className='py-2'>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {label} {required && <span className='text-util-colors-red-red-600'>*</span>}
        </label>
        {description && <div className='mb-2 text-xs text-text-tertiary'>{description}</div>}
        <select
          value={String(value)}
          onChange={e => onChange(e.target.value)}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value=''>Select...</option>
          {options?.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
    )
  }

  if (type === 'textarea') {
    return (
      <div className='py-2'>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {label} {required && <span className='text-util-colors-red-red-600'>*</span>}
        </label>
        {description && <div className='mb-2 text-xs text-text-tertiary'>{description}</div>}
        <textarea
          value={String(value)}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        />
      </div>
    )
  }

  return (
    <div className='py-2'>
      <label className='mb-1 block text-sm font-medium text-text-secondary'>
        {label} {required && <span className='text-util-colors-red-red-600'>*</span>}
      </label>
      {description && <div className='mb-2 text-xs text-text-tertiary'>{description}</div>}
      <Input
        type={type}
        value={String(value)}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  )
}

// Helper to safely get config value
const getConfigValue = <T,>(configs: ConfigsType, key: string, field: string, defaultValue: T): T => {
  const config = configs[key]
  if (!config)
    return defaultValue
  const value = config[field]
  if (value === undefined || value === null)
    return defaultValue
  return value as T
}

// =============================================================================
// API Keys Tab
// =============================================================================

type ApiKeysTabProps = {
  configs: ConfigsType
  onSave: (key: string, value: Record<string, unknown>) => void
  onTest: () => void
  isSaving: boolean
  isTesting: boolean
  testResult: { success: boolean; message: string } | null
}

const ApiKeysTab: FC<ApiKeysTabProps> = ({ configs, onSave, onTest, isSaving, isTesting, testResult }) => {
  const { t } = useTranslation()
  const [apifyKey, setApifyKey] = useState(getConfigValue(configs, 'apify_api_key', 'api_key', ''))

  const handleSave = () => {
    onSave('apify_api_key', { api_key: apifyKey })
  }

  return (
    <div className='space-y-6'>
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
        <div className='mb-4 flex items-center gap-2'>
          <RiKeyLine className='h-5 w-5 text-text-tertiary' />
          <h3 className='font-medium text-text-secondary'>Apify API</h3>
        </div>
        <p className='mb-4 text-sm text-text-tertiary'>
          {t('leads.settings.apify.description')}
        </p>
        <ConfigField
          label={t('leads.settings.apify.apiKey')}
          type='password'
          value={apifyKey}
          onChange={v => setApifyKey(String(v))}
          placeholder='apify_api_xxxxx'
          required
        />
        <div className='mt-4 flex items-center gap-3'>
          <Button variant='primary' onClick={handleSave} loading={isSaving}>
            <RiCheckLine className='mr-1 h-4 w-4' />
            {t('common.operation.save')}
          </Button>
          <Button variant='secondary' onClick={onTest} loading={isTesting}>
            {t('leads.settings.testConnection')}
          </Button>
          {testResult && (
            <span className={`text-sm ${testResult.success ? 'text-util-colors-green-green-600' : 'text-util-colors-red-red-600'}`}>
              {testResult.message}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Proxy Tab
// =============================================================================

type ProxyTabProps = {
  configs: ConfigsType
  onSave: (key: string, value: Record<string, unknown>) => void
  isSaving: boolean
}

const ProxyTab: FC<ProxyTabProps> = ({ configs, onSave, isSaving }) => {
  const { t } = useTranslation()
  const [provider, setProvider] = useState(getConfigValue(configs, 'proxy_pool_settings', 'provider', ''))
  const [poolSize, setPoolSize] = useState(getConfigValue(configs, 'proxy_pool_settings', 'pool_size', 10))
  const [rotationInterval, setRotationInterval] = useState(getConfigValue(configs, 'proxy_pool_settings', 'rotation_interval', 300))

  const handleSave = () => {
    onSave('proxy_pool_settings', {
      provider,
      pool_size: Number(poolSize),
      rotation_interval: Number(rotationInterval),
    })
  }

  return (
    <div className='space-y-6'>
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
        <div className='mb-4 flex items-center gap-2'>
          <RiServerLine className='h-5 w-5 text-text-tertiary' />
          <h3 className='font-medium text-text-secondary'>{t('leads.settings.proxy.title')}</h3>
        </div>
        <ConfigField
          label={t('leads.settings.proxy.provider')}
          type='select'
          value={provider}
          onChange={v => setProvider(String(v))}
          options={['brightdata', 'oxylabs', 'smartproxy']}
        />
        <ConfigField
          label={t('leads.settings.proxy.poolSize')}
          type='number'
          value={poolSize}
          onChange={v => setPoolSize(Number(v))}
        />
        <ConfigField
          label={t('leads.settings.proxy.rotationInterval')}
          description={t('leads.settings.proxy.rotationIntervalDesc')}
          type='number'
          value={rotationInterval}
          onChange={v => setRotationInterval(Number(v))}
        />
        <div className='mt-4'>
          <Button variant='primary' onClick={handleSave} loading={isSaving}>
            <RiCheckLine className='mr-1 h-4 w-4' />
            {t('common.operation.save')}
          </Button>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Browser Tab
// =============================================================================

type BrowserTabProps = {
  configs: ConfigsType
  onSave: (key: string, value: Record<string, unknown>) => void
  isSaving: boolean
}

const BrowserTab: FC<BrowserTabProps> = ({ configs, onSave, isSaving }) => {
  const { t } = useTranslation()
  const [provider, setProvider] = useState(getConfigValue(configs, 'browser_provider', 'provider', ''))
  const [email, setEmail] = useState(getConfigValue(configs, 'browser_credentials', 'email', ''))
  const [password, setPassword] = useState('')
  const [apiKey, setApiKey] = useState('')

  const handleSaveProvider = () => {
    onSave('browser_provider', { provider })
  }

  const handleSaveCredentials = () => {
    onSave('browser_credentials', { email, password, api_key: apiKey })
  }

  return (
    <div className='space-y-6'>
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
        <div className='mb-4 flex items-center gap-2'>
          <RiSettings3Line className='h-5 w-5 text-text-tertiary' />
          <h3 className='font-medium text-text-secondary'>{t('leads.settings.browser.title')}</h3>
        </div>
        <ConfigField
          label={t('leads.settings.browser.provider')}
          type='select'
          value={provider}
          onChange={v => setProvider(String(v))}
          options={['multilogin', 'gologin', 'adspower']}
        />
        <div className='mt-4'>
          <Button variant='primary' onClick={handleSaveProvider} loading={isSaving}>
            <RiCheckLine className='mr-1 h-4 w-4' />
            {t('common.operation.save')}
          </Button>
        </div>
      </div>

      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
        <div className='mb-4 flex items-center gap-2'>
          <RiKeyLine className='h-5 w-5 text-text-tertiary' />
          <h3 className='font-medium text-text-secondary'>{t('leads.settings.browser.credentials')}</h3>
        </div>
        <ConfigField
          label={t('leads.settings.browser.email')}
          type='email'
          value={email}
          onChange={v => setEmail(String(v))}
          required
        />
        <ConfigField
          label={t('leads.settings.browser.password')}
          type='password'
          value={password}
          onChange={v => setPassword(String(v))}
          required
        />
        <ConfigField
          label={t('leads.settings.browser.apiKey')}
          type='password'
          value={apiKey}
          onChange={v => setApiKey(String(v))}
        />
        <div className='mt-4'>
          <Button variant='primary' onClick={handleSaveCredentials} loading={isSaving}>
            <RiCheckLine className='mr-1 h-4 w-4' />
            {t('common.operation.save')}
          </Button>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Workflow Bindings Tab
// =============================================================================

const WorkflowBindingsTab: FC = () => {
  const { t } = useTranslation()

  return (
    <div className='space-y-6'>
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
        <div className='mb-4 flex items-center gap-2'>
          <RiLink className='h-5 w-5 text-text-tertiary' />
          <h3 className='font-medium text-text-secondary'>{t('leads.settings.bindings.title')}</h3>
        </div>
        <p className='text-sm text-text-tertiary'>
          {t('leads.settings.bindings.description')}
        </p>
        <div className='mt-4 text-center text-text-quaternary'>
          Coming soon...
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Notifications Tab
// =============================================================================

type NotificationsTabProps = {
  configs: ConfigsType
  onSave: (key: string, value: Record<string, unknown>) => void
  isSaving: boolean
}

const NotificationsTab: FC<NotificationsTabProps> = ({ configs, onSave, isSaving }) => {
  const { t } = useTranslation()
  const [emailEnabled, setEmailEnabled] = useState(getConfigValue(configs, 'notification_settings', 'email_enabled', false))
  const [emailAddress, setEmailAddress] = useState(getConfigValue(configs, 'notification_settings', 'email_address', ''))
  const [webhookEnabled, setWebhookEnabled] = useState(getConfigValue(configs, 'notification_settings', 'webhook_enabled', false))
  const [webhookUrl, setWebhookUrl] = useState(getConfigValue(configs, 'notification_settings', 'webhook_url', ''))

  const handleSave = () => {
    onSave('notification_settings', {
      email_enabled: emailEnabled,
      email_address: emailAddress,
      webhook_enabled: webhookEnabled,
      webhook_url: webhookUrl,
    })
  }

  return (
    <div className='space-y-6'>
      <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
        <div className='mb-4 flex items-center gap-2'>
          <RiNotification3Line className='h-5 w-5 text-text-tertiary' />
          <h3 className='font-medium text-text-secondary'>{t('leads.settings.notifications.title')}</h3>
        </div>
        <ConfigField
          label={t('leads.settings.notifications.emailEnabled')}
          type='boolean'
          value={emailEnabled}
          onChange={v => setEmailEnabled(Boolean(v))}
        />
        {emailEnabled && (
          <ConfigField
            label={t('leads.settings.notifications.emailAddress')}
            type='email'
            value={emailAddress}
            onChange={v => setEmailAddress(String(v))}
          />
        )}
        <div className='my-4 border-t border-divider-subtle' />
        <ConfigField
          label={t('leads.settings.notifications.webhookEnabled')}
          type='boolean'
          value={webhookEnabled}
          onChange={v => setWebhookEnabled(Boolean(v))}
        />
        {webhookEnabled && (
          <ConfigField
            label={t('leads.settings.notifications.webhookUrl')}
            type='url'
            value={webhookUrl}
            onChange={v => setWebhookUrl(String(v))}
            placeholder='https://...'
          />
        )}
        <div className='mt-4'>
          <Button variant='primary' onClick={handleSave} loading={isSaving}>
            <RiCheckLine className='mr-1 h-4 w-4' />
            {t('common.operation.save')}
          </Button>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Settings Page
// =============================================================================

const SettingsPage: FC = () => {
  const { t } = useTranslation()
  const router = useRouter()
  useDocumentTitle(t('leads.settings.title'))

  const [activeTab, setActiveTab] = useState('api-keys')
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const { data, isLoading, refetch } = useLeadsConfigs()
  const updateConfig = useUpdateLeadsConfig()
  const testConnection = useTestConnection()

  const configs: ConfigsType = data?.configs || {}

  const handleSave = useCallback(async (key: string, value: Record<string, unknown>) => {
    try {
      await updateConfig.mutateAsync({ configKey: key, configValue: value })
      Toast.notify({ type: 'success', message: t('leads.settings.saved') })
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.settings.saveFailed') })
    }
  }, [updateConfig, refetch, t])

  const handleTest = useCallback(async () => {
    setTestResult(null)
    try {
      const result = await testConnection.mutateAsync()
      setTestResult(result)
    }
    catch {
      setTestResult({ success: false, message: 'Connection test failed' })
    }
  }, [testConnection])

  const tabs = [
    { value: 'api-keys', text: t('leads.settings.tabs.apiKeys') },
    { value: 'proxy', text: t('leads.settings.tabs.proxy') },
    { value: 'browser', text: t('leads.settings.tabs.browser') },
    { value: 'bindings', text: t('leads.settings.tabs.bindings') },
    { value: 'notifications', text: t('leads.settings.tabs.notifications') },
  ]

  if (isLoading) {
    return (
      <div className='flex h-[400px] items-center justify-center'>
        <Loading type='area' />
      </div>
    )
  }

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      {/* Header */}
      <div className='sticky top-0 z-10 flex items-center justify-between bg-background-body px-12 pb-5 pt-7'>
        <div className='flex items-center gap-3'>
          <Button variant='ghost' size='small' onClick={() => router.push('/leads')}>
            <RiArrowLeftLine className='h-4 w-4' />
          </Button>
          <h1 className='text-xl font-semibold text-text-primary'>{t('leads.settings.title')}</h1>
        </div>
      </div>

      {/* Tabs */}
      <div className='px-12 pb-4'>
        <TabSliderNew
          value={activeTab}
          onChange={setActiveTab}
          options={tabs}
        />
      </div>

      {/* Content */}
      <div className='px-12 pb-8'>
        {activeTab === 'api-keys' && (
          <ApiKeysTab
            configs={configs}
            onSave={handleSave}
            onTest={handleTest}
            isSaving={updateConfig.isPending}
            isTesting={testConnection.isPending}
            testResult={testResult}
          />
        )}
        {activeTab === 'proxy' && (
          <ProxyTab
            configs={configs}
            onSave={handleSave}
            isSaving={updateConfig.isPending}
          />
        )}
        {activeTab === 'browser' && (
          <BrowserTab
            configs={configs}
            onSave={handleSave}
            isSaving={updateConfig.isPending}
          />
        )}
        {activeTab === 'bindings' && <WorkflowBindingsTab />}
        {activeTab === 'notifications' && (
          <NotificationsTab
            configs={configs}
            onSave={handleSave}
            isSaving={updateConfig.isPending}
          />
        )}
      </div>
    </div>
  )
}

export default SettingsPage
