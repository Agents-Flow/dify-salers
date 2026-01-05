'use client'

import {
  RiUserSearchFill,
  RiUserSearchLine,
} from '@remixicon/react'
import Link from 'next/link'
import { useSelectedLayoutSegment } from 'next/navigation'
import { useTranslation } from 'react-i18next'
import { cn } from '@/utils/classnames'

type LeadsNavProps = {
  className?: string
}

const LeadsNav = ({
  className,
}: LeadsNavProps) => {
  const { t } = useTranslation()
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'leads'

  return (
    <Link
      href="/leads/outreach"
      className={cn('group text-sm font-medium', activated && 'hover:bg-components-main-nav-nav-button-bg-active-hover bg-components-main-nav-nav-button-bg-active font-semibold shadow-md', activated ? 'text-components-main-nav-nav-button-text-active' : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover', className)}
    >
      {
        activated
          ? <RiUserSearchFill className="h-4 w-4" />
          : <RiUserSearchLine className="h-4 w-4" />
      }
      <div className="ml-2 max-[1024px]:hidden">
        {t('menus.leads', { ns: 'common' })}
      </div>
    </Link>
  )
}

export default LeadsNav
