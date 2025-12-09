'use client'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiCheckboxCircleLine,
  RiGroupLine,
  RiHeartPulseLine,
  RiMessage2Line,
  RiRefreshLine,
  RiRobotLine,
  RiUserFollowLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Loading from '@/app/components/base/loading'
import {
  useAIStatus,
  useDashboardOverview,
  useTargetKOLList,
} from '@/service/use-leads'

// =============================================================================
// Stat Card Component
// =============================================================================

type StatCardProps = {
  icon: React.ReactNode
  label: string
  value: string | number
  subtext?: string
  color?: 'blue' | 'green' | 'orange' | 'gray'
}

const StatCard: FC<StatCardProps> = ({ icon, label, value, subtext, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    green: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    orange: 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600',
    gray: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
  }

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <div className='mb-3 flex items-center gap-3'>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        <span className='text-sm text-text-tertiary'>{label}</span>
      </div>
      <div className='text-2xl font-semibold text-text-primary'>{value}</div>
      {subtext && <p className='mt-1 text-xs text-text-tertiary'>{subtext}</p>}
    </div>
  )
}

// =============================================================================
// Funnel Chart Component
// =============================================================================

type FunnelChartProps = {
  data: {
    total_followers: number
    followed: number
    follow_backs: number
    dm_sent: number
    converted: number
    follow_back_rate: number
    dm_response_rate: number
    conversion_rate: number
  }
}

const FunnelChart: FC<FunnelChartProps> = ({ data }) => {
  const { t } = useTranslation()

  const stages = [
    { label: t('dashboard.funnel.scraped'), value: data.total_followers, color: 'bg-util-colors-gray-gray-300' },
    { label: t('dashboard.funnel.followed'), value: data.followed, color: 'bg-util-colors-blue-blue-400' },
    { label: t('dashboard.funnel.followBacks'), value: data.follow_backs, color: 'bg-util-colors-indigo-indigo-400' },
    { label: t('dashboard.funnel.dmSent'), value: data.dm_sent, color: 'bg-util-colors-orange-orange-400' },
    { label: t('dashboard.funnel.converted'), value: data.converted, color: 'bg-util-colors-green-green-500' },
  ]

  const maxValue = Math.max(...stages.map(s => s.value), 1)

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <h3 className='mb-4 font-medium text-text-secondary'>{t('dashboard.funnel.title')}</h3>
      <div className='space-y-3'>
        {stages.map((stage, index) => {
          const width = (stage.value / maxValue) * 100
          return (
            <div key={index}>
              <div className='mb-1 flex items-center justify-between text-sm'>
                <span className='text-text-tertiary'>{stage.label}</span>
                <span className='font-medium text-text-secondary'>{stage.value.toLocaleString()}</span>
              </div>
              <div className='h-6 w-full overflow-hidden rounded-lg bg-background-default'>
                <div
                  className={`h-full ${stage.color} transition-all duration-500`}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
      <div className='mt-4 grid grid-cols-3 gap-4 border-t border-divider-subtle pt-4'>
        <div className='text-center'>
          <div className='text-lg font-semibold text-util-colors-blue-blue-600'>{data.follow_back_rate}%</div>
          <div className='text-xs text-text-tertiary'>{t('dashboard.rate.followBack')}</div>
        </div>
        <div className='text-center'>
          <div className='text-lg font-semibold text-util-colors-orange-orange-600'>{data.dm_response_rate}%</div>
          <div className='text-xs text-text-tertiary'>{t('dashboard.rate.dmResponse')}</div>
        </div>
        <div className='text-center'>
          <div className='text-lg font-semibold text-util-colors-green-green-600'>{data.conversion_rate}%</div>
          <div className='text-xs text-text-tertiary'>{t('dashboard.rate.conversion')}</div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// AI Status Card
// =============================================================================

type AIStatusCardProps = {
  conversationAI: { enabled: boolean; configured: boolean }
  followerScraper: { enabled: boolean; configured: boolean }
}

const AIStatusCard: FC<AIStatusCardProps> = ({ conversationAI, followerScraper }) => {
  const { t } = useTranslation()

  const StatusBadge: FC<{ enabled: boolean; configured: boolean }> = ({ enabled, configured }) => {
    if (!enabled) {
      return (
        <span className='inline-flex items-center rounded-md bg-util-colors-gray-gray-100 px-2 py-1 text-xs text-util-colors-gray-gray-600'>
          {t('dashboard.ai.disabled')}
        </span>
      )
    }
    if (!configured) {
      return (
        <span className='inline-flex items-center rounded-md bg-util-colors-orange-orange-50 px-2 py-1 text-xs text-util-colors-orange-orange-600'>
          {t('dashboard.ai.notConfigured')}
        </span>
      )
    }
    return (
      <span className='inline-flex items-center rounded-md bg-util-colors-green-green-50 px-2 py-1 text-xs text-util-colors-green-green-600'>
        {t('dashboard.ai.ready')}
      </span>
    )
  }

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <h3 className='mb-4 font-medium text-text-secondary'>{t('dashboard.ai.title')}</h3>
      <div className='space-y-3'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center gap-2'>
            <RiRobotLine className='h-4 w-4 text-text-tertiary' />
            <span className='text-sm text-text-secondary'>{t('dashboard.ai.conversationAI')}</span>
          </div>
          <StatusBadge enabled={conversationAI.enabled} configured={conversationAI.configured} />
        </div>
        <div className='flex items-center justify-between'>
          <div className='flex items-center gap-2'>
            <RiUserFollowLine className='h-4 w-4 text-text-tertiary' />
            <span className='text-sm text-text-secondary'>{t('dashboard.ai.followerScraper')}</span>
          </div>
          <StatusBadge enabled={followerScraper.enabled} configured={followerScraper.configured} />
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Dashboard Page
// =============================================================================

const DashboardPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('dashboard.title'))

  const { data: overview, isLoading, refetch } = useDashboardOverview()
  const { data: aiStatus } = useAIStatus()
  const { data: kols } = useTargetKOLList({ limit: 5 })

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
        <h1 className='text-xl font-semibold text-text-primary'>{t('dashboard.title')}</h1>
        <Button variant='secondary' onClick={() => refetch()}>
          <RiRefreshLine className='mr-1 h-4 w-4' />
          {t('common.operation.refresh')}
        </Button>
      </div>

      {/* Content */}
      <div className='space-y-6 px-12 pb-8'>
        {/* Stats Grid */}
        <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4'>
          <StatCard
            icon={<RiGroupLine className='h-5 w-5' />}
            label={t('dashboard.stats.targetKols')}
            value={overview?.kols.total || 0}
            color='blue'
          />
          <StatCard
            icon={<RiHeartPulseLine className='h-5 w-5' />}
            label={t('dashboard.stats.healthyAccounts')}
            value={`${overview?.accounts.healthy || 0}/${overview?.accounts.total || 0}`}
            subtext={`${overview?.accounts.health_rate || 0}% healthy`}
            color={overview && overview.accounts.health_rate >= 80 ? 'green' : 'orange'}
          />
          <StatCard
            icon={<RiMessage2Line className='h-5 w-5' />}
            label={t('dashboard.stats.activeConversations')}
            value={overview?.conversations.active || 0}
            subtext={`${overview?.conversations.needs_human || 0} needs human`}
            color={overview && overview.conversations.needs_human > 0 ? 'orange' : 'blue'}
          />
          <StatCard
            icon={<RiCheckboxCircleLine className='h-5 w-5' />}
            label={t('dashboard.stats.conversions')}
            value={overview?.funnel.converted || 0}
            subtext={`${overview?.funnel.conversion_rate || 0}% conversion rate`}
            color='green'
          />
        </div>

        {/* Main Content Grid */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-3'>
          {/* Funnel Chart - Takes 2 columns */}
          <div className='lg:col-span-2'>
            {overview?.funnel && <FunnelChart data={overview.funnel} />}
          </div>

          {/* Right Column */}
          <div className='space-y-6'>
            {/* AI Status */}
            {aiStatus && (
              <AIStatusCard
                conversationAI={aiStatus.conversation_ai}
                followerScraper={aiStatus.follower_scraper}
              />
            )}

            {/* Target KOLs Quick View */}
            <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
              <h3 className='mb-4 font-medium text-text-secondary'>{t('dashboard.kols.title')}</h3>
              {kols?.data?.length
                ? (
                  <div className='space-y-3'>
                    {kols.data.slice(0, 5).map(kol => (
                      <div key={kol.id} className='flex items-center justify-between'>
                        <div className='flex items-center gap-2'>
                          <span className='text-sm'>
                            {kol.platform === 'x' ? '𝕏' : '📸'}
                          </span>
                          <span className='text-sm text-text-secondary'>@{kol.username}</span>
                        </div>
                        <span className='text-xs text-text-tertiary'>
                          {kol.follower_count.toLocaleString()} followers
                        </span>
                      </div>
                    ))}
                  </div>
                )
                : (
                  <p className='text-sm text-text-tertiary'>{t('dashboard.kols.empty')}</p>
                )}
            </div>

            {/* Quick Stats */}
            <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
              <h3 className='mb-4 font-medium text-text-secondary'>{t('dashboard.quickStats.title')}</h3>
              <div className='space-y-2 text-sm'>
                <div className='flex items-center justify-between'>
                  <span className='text-text-tertiary'>{t('dashboard.quickStats.totalFollowers')}</span>
                  <span className='font-medium text-text-secondary'>
                    {overview?.funnel.total_followers.toLocaleString() || 0}
                  </span>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-text-tertiary'>{t('dashboard.quickStats.totalConversations')}</span>
                  <span className='font-medium text-text-secondary'>
                    {overview?.conversations.total.toLocaleString() || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
