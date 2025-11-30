/**
 * LeadsNav - Lead acquisition navigation component
 * Following Dify's navigation component patterns
 * Reference: web/app/components/header/tools-nav/index.tsx
 */
'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { useSelectedLayoutSegment } from 'next/navigation'
import { RiUserSearchLine } from '@remixicon/react'
import classNames from '@/utils/classnames'

type Props = {
  className?: string
}

const LeadsNav: FC<Props> = ({ className }) => {
  const { t } = useTranslation()
  const selectedSegment = useSelectedLayoutSegment()
  const isActive = selectedSegment === 'leads'

  return (
    <Link
      href="/leads"
      className={classNames(
        className,
        'group',
        isActive
          ? 'bg-components-main-nav-nav-button-bg-active text-components-main-nav-nav-button-text-active'
          : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover hover:text-components-main-nav-nav-button-text-active',
      )}
    >
      <RiUserSearchLine className='mr-1 h-4 w-4' />
      {t('common.menus.leads')}
    </Link>
  )
}

export default LeadsNav
