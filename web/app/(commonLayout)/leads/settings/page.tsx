'use client'
import type { FC } from 'react'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiSaveLine,
  RiSettings4Line,
  RiTestTubeLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'
import LeadsNav from '../components/leads-nav'
import {
  useLeadsConfigs,
  useTestLeadsConnection,
  useUpdateLeadsConfig,
} from '@/service/use-leads'

const SettingsPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.nav.settings'))

  const { data: configsData, isLoading } = useLeadsConfigs()
  const updateConfig = useUpdateLeadsConfig()
  const testConnection = useTestLeadsConnection()

  const [apifyToken, setApifyToken] = useState('')

  const handleSaveApifyToken = useCallback(async () => {
    if (!apifyToken.trim()) {
      Toast.notify({ type: 'error', message: t('leads.settings.tokenRequired') })
      return
    }
    try {
      await updateConfig.mutateAsync({ key: 'apify_api_token', value: apifyToken })
      Toast.notify({ type: 'success', message: t('leads.settings.saved') })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.settings.saveFailed') })
    }
  }, [apifyToken, updateConfig, t])

  const handleTestConnection = useCallback(async () => {
    try {
      const result = await testConnection.mutateAsync()
      if (result.success) {
        Toast.notify({ type: 'success', message: t('leads.settings.connectionSuccess') })
      }
      else {
        Toast.notify({ type: 'error', message: result.message || t('leads.settings.connectionFailed') })
      }
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.settings.connectionFailed') })
    }
  }, [testConnection, t])

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      <div className='flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-4'>
        <h1 className='text-xl font-semibold text-text-primary'>{t('leads.nav.settings')}</h1>
      </div>
      <div className='px-12 pb-6'>
        {isLoading
          ? (
            <div className='flex h-[200px] items-center justify-center'>
              <Loading type='area' />
            </div>
          )
          : (
            <div className='max-w-2xl space-y-6'>
              {/* Apify Configuration */}
              <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-6'>
                <div className='mb-4 flex items-center gap-2'>
                  <RiSettings4Line className='h-5 w-5 text-text-secondary' />
                  <h2 className='text-lg font-medium text-text-secondary'>{t('leads.settings.apifyConfig')}</h2>
                </div>
                <p className='mb-4 text-sm text-text-tertiary'>{t('leads.settings.apifyDesc')}</p>
                <div className='space-y-4'>
                  <div>
                    <label className='mb-1 block text-sm font-medium text-text-secondary'>
                      {t('leads.settings.apifyToken')}
                    </label>
                    <Input
                      type='password'
                      value={apifyToken}
                      onChange={e => setApifyToken(e.target.value)}
                      placeholder={configsData?.configs?.apify_api_token ? '••••••••' : t('leads.settings.apifyTokenPlaceholder')}
                    />
                  </div>
                  <div className='flex gap-2'>
                    <Button
                      variant='primary'
                      onClick={handleSaveApifyToken}
                      loading={updateConfig.isPending}
                    >
                      <RiSaveLine className='mr-1 h-4 w-4' />
                      {t('common.operation.save')}
                    </Button>
                    <Button
                      variant='secondary'
                      onClick={handleTestConnection}
                      loading={testConnection.isPending}
                    >
                      <RiTestTubeLine className='mr-1 h-4 w-4' />
                      {t('leads.settings.testConnection')}
                    </Button>
                  </div>
                </div>
              </div>

              {/* Current Status */}
              <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-6'>
                <h2 className='mb-4 text-lg font-medium text-text-secondary'>{t('leads.settings.status')}</h2>
                <div className='space-y-2 text-sm'>
                  <div className='flex items-center justify-between'>
                    <span className='text-text-tertiary'>{t('leads.settings.scraperEnabled')}</span>
                    <span className={configsData?.configs?.apify_api_token ? 'text-util-colors-green-green-600' : 'text-util-colors-gray-gray-600'}>
                      {configsData?.configs?.apify_api_token ? t('common.operation.enabled') : t('common.operation.disabled')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
      </div>
    </div>
  )
}

export default SettingsPage
