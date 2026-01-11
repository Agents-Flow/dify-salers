'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import { RiRobotLine } from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import LeadsNav from '../components/leads-nav'

const AutomationPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.nav.automation'))

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      <div className='flex flex-1 flex-col items-center justify-center px-12 py-8'>
        <div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-util-colors-blue-blue-50'>
          <RiRobotLine className='h-10 w-10 text-util-colors-blue-blue-600' />
        </div>
        <h2 className='mt-6 text-xl font-semibold text-text-primary'>
          {t('leads.nav.automation')}
        </h2>
        <p className='mt-2 text-center text-sm text-text-tertiary'>
          Automation features coming soon. Configure automated follow-ups, DM sequences, and more.
        </p>
      </div>
    </div>
  )
}

export default AutomationPage
