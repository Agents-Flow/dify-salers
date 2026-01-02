'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import {
  RiBarChartBoxLine,
  RiInboxLine,
  RiRobotLine,
  RiSendPlaneLine,
  RiSettings4Line,
  RiTaskLine,
  RiUserSearchLine,
} from '@remixicon/react'
import classNames from '@/utils/classnames'

type NavItem = {
  key: string
  label: string
  icon: FC<{ className?: string }>
  href: string
}

const LeadsNav: FC = () => {
  const { t } = useTranslation()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const navItems: NavItem[] = [
    {
      key: 'leads',
      label: t('leads.nav.leads'),
      icon: RiUserSearchLine,
      href: '/leads',
    },
    {
      key: 'tasks',
      label: t('leads.nav.tasks'),
      icon: RiTaskLine,
      href: '/leads?tab=tasks',
    },
    {
      key: 'outreach',
      label: t('leads.nav.outreach'),
      icon: RiSendPlaneLine,
      href: '/leads/outreach',
    },
    {
      key: 'inbox',
      label: t('leads.nav.inbox'),
      icon: RiInboxLine,
      href: '/leads/inbox',
    },
    {
      key: 'automation',
      label: t('leads.nav.automation'),
      icon: RiRobotLine,
      href: '/leads/automation',
    },
    {
      key: 'dashboard',
      label: t('leads.nav.dashboard'),
      icon: RiBarChartBoxLine,
      href: '/leads/dashboard',
    },
    {
      key: 'settings',
      label: t('leads.nav.settings'),
      icon: RiSettings4Line,
      href: '/leads/settings',
    },
  ]

  const isActive = (item: NavItem): boolean => {
    if (item.key === 'tasks') {
      return pathname === '/leads' && searchParams.get('tab') === 'tasks'
    }
    if (item.key === 'leads') {
      return pathname === '/leads' && searchParams.get('tab') !== 'tasks'
    }
    return pathname === item.href || pathname.startsWith(`${item.href}/`)
  }

  const handleNavigate = (item: NavItem) => {
    router.push(item.href)
  }

  return (
    <div className='flex items-center gap-1 border-b border-divider-subtle bg-background-body px-12 py-2'>
      {navItems.map(item => (
        <button
          key={item.key}
          onClick={() => handleNavigate(item)}
          className={classNames(
            'flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            isActive(item)
              ? 'bg-state-accent-active text-text-accent'
              : 'text-text-tertiary hover:bg-state-base-hover hover:text-text-secondary',
          )}
        >
          <item.icon className='h-4 w-4' />
          {item.label}
        </button>
      ))}
    </div>
  )
}

export default LeadsNav
