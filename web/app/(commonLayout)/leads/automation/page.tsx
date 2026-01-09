'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiAddLine,
  RiRefreshLine,
  RiRobotLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import LeadsNav from '../components/leads-nav'

const AutomationPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.nav.automation'))

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      <div className='flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-4'>
        <h1 className='text-xl font-semibold text-text-primary'>{t('leads.nav.automation')}</h1>
        <div className='flex items-center gap-2'>
          <Button variant='secondary'>
            <RiRefreshLine className='h-4 w-4' />
          </Button>
          <Button variant='primary'>
            <RiAddLine className='mr-1 h-4 w-4' />
            {t('leads.automation.create')}
          </Button>
        </div>
      </div>
      <div className='flex flex-1 flex-col items-center justify-center px-12 pb-6'>
        <RiRobotLine className='mb-4 h-16 w-16 text-text-quaternary' />
        <h2 className='mb-2 text-lg font-medium text-text-secondary'>{t('leads.automation.empty')}</h2>
        <p className='text-sm text-text-tertiary'>{t('leads.automation.emptyDesc')}</p>
      </div>
    </div>
  )
}

export default AutomationPage
