'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiInboxLine,
  RiRefreshLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import LeadsNav from '../components/leads-nav'

const InboxPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.nav.inbox'))

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      <div className='flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-4'>
        <h1 className='text-xl font-semibold text-text-primary'>{t('leads.nav.inbox')}</h1>
        <Button variant='secondary'>
          <RiRefreshLine className='h-4 w-4' />
        </Button>
      </div>
      <div className='flex flex-1 flex-col items-center justify-center px-12 pb-6'>
        <RiInboxLine className='mb-4 h-16 w-16 text-text-quaternary' />
        <h2 className='mb-2 text-lg font-medium text-text-secondary'>{t('leads.inbox.empty')}</h2>
        <p className='text-sm text-text-tertiary'>{t('leads.inbox.emptyDesc')}</p>
      </div>
    </div>
  )
}

export default InboxPage
