'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiBarChartBoxLine,
  RiRefreshLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Loading from '@/app/components/base/loading'
import LeadsNav from '../components/leads-nav'
import { useLeadsAnalyticsOverview } from '@/service/use-leads'

const DashboardPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.nav.dashboard'))

  const { data: overview, isLoading, refetch } = useLeadsAnalyticsOverview()

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      <div className='flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-4'>
        <h1 className='text-xl font-semibold text-text-primary'>{t('leads.nav.dashboard')}</h1>
        <Button variant='secondary' onClick={() => refetch()}>
          <RiRefreshLine className='h-4 w-4' />
        </Button>
      </div>
      <div className='px-12 pb-6'>
        {isLoading
          ? (
            <div className='flex h-[200px] items-center justify-center'>
              <Loading type='area' />
            </div>
          )
          : overview
            ? (
              <div className='grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4'>
                <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
                  <div className='mb-2 text-sm text-text-tertiary'>{t('leads.dashboard.totalLeads')}</div>
                  <div className='text-2xl font-semibold text-text-primary'>{overview.total_leads || 0}</div>
                </div>
                <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
                  <div className='mb-2 text-sm text-text-tertiary'>{t('leads.dashboard.totalTasks')}</div>
                  <div className='text-2xl font-semibold text-text-primary'>{overview.total_tasks || 0}</div>
                </div>
                <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
                  <div className='mb-2 text-sm text-text-tertiary'>{t('leads.dashboard.totalKols')}</div>
                  <div className='text-2xl font-semibold text-text-primary'>{overview.total_kols || 0}</div>
                </div>
                <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4'>
                  <div className='mb-2 text-sm text-text-tertiary'>{t('leads.dashboard.totalAccounts')}</div>
                  <div className='text-2xl font-semibold text-text-primary'>{overview.total_accounts || 0}</div>
                </div>
              </div>
            )
            : (
              <div className='flex flex-1 flex-col items-center justify-center py-12'>
                <RiBarChartBoxLine className='mb-4 h-16 w-16 text-text-quaternary' />
                <h2 className='mb-2 text-lg font-medium text-text-secondary'>{t('leads.dashboard.empty')}</h2>
                <p className='text-sm text-text-tertiary'>{t('leads.dashboard.emptyDesc')}</p>
              </div>
            )}
      </div>
    </div>
  )
}

export default DashboardPage
