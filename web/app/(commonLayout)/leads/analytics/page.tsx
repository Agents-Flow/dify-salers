'use client'
import type { FC } from 'react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from 'next/navigation'
import {
  RiArrowLeftLine,
  RiBarChartLine,
  RiFilter2Line,
  RiFilter3Line,
  RiLineChartLine,
  RiRefreshLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Loading from '@/app/components/base/loading'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import {
  useAnalyticsDailyStats,
  useAnalyticsFunnel,
  useAnalyticsKOLPerformance,
  useAnalyticsTaskSummary,
} from '@/service/use-leads-analytics'

// =============================================================================
// Funnel Chart Component
// =============================================================================

type FunnelData = {
  total_followers: number
  followed: number
  follow_backs: number
  dm_sent: number
  converted: number
  follow_back_rate: number
  dm_response_rate: number
  conversion_rate: number
}

const FunnelChart: FC<{ data: FunnelData }> = ({ data }) => {
  const { t } = useTranslation()

  const stages = [
    { label: t('leads.analytics.funnel.scraped'), value: data.total_followers, color: 'bg-util-colors-gray-gray-300' },
    { label: t('leads.analytics.funnel.followed'), value: data.followed, color: 'bg-util-colors-blue-blue-400' },
    { label: t('leads.analytics.funnel.followBacks'), value: data.follow_backs, color: 'bg-util-colors-indigo-indigo-400' },
    { label: t('leads.analytics.funnel.dmSent'), value: data.dm_sent, color: 'bg-util-colors-orange-orange-400' },
    { label: t('leads.analytics.funnel.converted'), value: data.converted, color: 'bg-util-colors-green-green-500' },
  ]

  const maxValue = Math.max(...stages.map(s => s.value), 1)

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <div className='mb-4 flex items-center gap-2'>
        <RiFilter2Line className='h-5 w-5 text-text-tertiary' />
        <h3 className='font-medium text-text-secondary'>{t('leads.analytics.funnel.title')}</h3>
      </div>
      <div className='space-y-3'>
        {stages.map((stage, index) => {
          const width = (stage.value / maxValue) * 100
          return (
            <div key={index}>
              <div className='mb-1 flex items-center justify-between text-sm'>
                <span className='text-text-tertiary'>{stage.label}</span>
                <span className='font-medium text-text-secondary'>{stage.value.toLocaleString()}</span>
              </div>
              <div className='h-8 w-full overflow-hidden rounded-lg bg-background-default'>
                <div
                  className={`h-full ${stage.color} transition-all duration-500`}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
      <div className='mt-6 grid grid-cols-3 gap-4 border-t border-divider-subtle pt-4'>
        <div className='text-center'>
          <div className='text-2xl font-semibold text-util-colors-blue-blue-600'>{data.follow_back_rate}%</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.rate.followBack')}</div>
        </div>
        <div className='text-center'>
          <div className='text-2xl font-semibold text-util-colors-orange-orange-600'>{data.dm_response_rate}%</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.rate.dmResponse')}</div>
        </div>
        <div className='text-center'>
          <div className='text-2xl font-semibold text-util-colors-green-green-600'>{data.conversion_rate}%</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.rate.conversion')}</div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// KOL Performance Table
// =============================================================================

type KOLPerformance = {
  kol_id: string
  username: string
  platform: string
  follower_count: number
  scraped_followers: number
  conversions: number
  conversion_rate: number
}

const KOLPerformanceTable: FC<{ data: KOLPerformance[] }> = ({ data }) => {
  const { t } = useTranslation()

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <div className='mb-4 flex items-center gap-2'>
        <RiBarChartLine className='h-5 w-5 text-text-tertiary' />
        <h3 className='font-medium text-text-secondary'>{t('leads.analytics.kolPerformance.title')}</h3>
      </div>
      <div className='overflow-x-auto'>
        <table className='w-full'>
          <thead>
            <tr className='border-b border-divider-subtle'>
              <th className='px-3 py-2 text-left text-xs font-medium text-text-tertiary'>KOL</th>
              <th className='px-3 py-2 text-left text-xs font-medium text-text-tertiary'>{t('leads.analytics.kolPerformance.platform')}</th>
              <th className='px-3 py-2 text-right text-xs font-medium text-text-tertiary'>{t('leads.analytics.kolPerformance.followers')}</th>
              <th className='px-3 py-2 text-right text-xs font-medium text-text-tertiary'>{t('leads.analytics.kolPerformance.scraped')}</th>
              <th className='px-3 py-2 text-right text-xs font-medium text-text-tertiary'>{t('leads.analytics.kolPerformance.conversions')}</th>
              <th className='px-3 py-2 text-right text-xs font-medium text-text-tertiary'>{t('leads.analytics.kolPerformance.rate')}</th>
            </tr>
          </thead>
          <tbody>
            {data.map(kol => (
              <tr key={kol.kol_id} className='border-b border-divider-subtle last:border-0'>
                <td className='px-3 py-3 text-sm text-text-secondary'>@{kol.username}</td>
                <td className='px-3 py-3'>
                  <span className='inline-flex items-center rounded-md bg-util-colors-blue-blue-50 px-2 py-1 text-xs text-util-colors-blue-blue-600'>
                    {kol.platform}
                  </span>
                </td>
                <td className='px-3 py-3 text-right text-sm text-text-tertiary'>{kol.follower_count.toLocaleString()}</td>
                <td className='px-3 py-3 text-right text-sm text-text-secondary'>{kol.scraped_followers.toLocaleString()}</td>
                <td className='px-3 py-3 text-right text-sm font-medium text-util-colors-green-green-600'>{kol.conversions}</td>
                <td className='px-3 py-3 text-right text-sm text-text-secondary'>{kol.conversion_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 && (
          <div className='py-8 text-center text-text-tertiary'>
            {t('leads.analytics.kolPerformance.empty')}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Daily Stats Chart
// =============================================================================

type DailyStat = {
  date: string
  scraped: number
  followed: number
  dm_sent: number
  converted: number
}

const DailyStatsChart: FC<{ data: DailyStat[] }> = ({ data }) => {
  const { t } = useTranslation()

  // Simple bar chart representation
  const maxValue = Math.max(...data.flatMap(d => [d.scraped, d.followed, d.dm_sent, d.converted]), 1)

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <div className='mb-4 flex items-center gap-2'>
        <RiLineChartLine className='h-5 w-5 text-text-tertiary' />
        <h3 className='font-medium text-text-secondary'>{t('leads.analytics.dailyStats.title')}</h3>
      </div>
      <div className='mb-4 flex items-center gap-4 text-xs'>
        <div className='flex items-center gap-1'>
          <div className='h-3 w-3 rounded bg-util-colors-gray-gray-400' />
          <span className='text-text-tertiary'>{t('leads.analytics.dailyStats.scraped')}</span>
        </div>
        <div className='flex items-center gap-1'>
          <div className='h-3 w-3 rounded bg-util-colors-blue-blue-400' />
          <span className='text-text-tertiary'>{t('leads.analytics.dailyStats.followed')}</span>
        </div>
        <div className='flex items-center gap-1'>
          <div className='h-3 w-3 rounded bg-util-colors-orange-orange-400' />
          <span className='text-text-tertiary'>{t('leads.analytics.dailyStats.dmSent')}</span>
        </div>
        <div className='flex items-center gap-1'>
          <div className='h-3 w-3 rounded bg-util-colors-green-green-500' />
          <span className='text-text-tertiary'>{t('leads.analytics.dailyStats.converted')}</span>
        </div>
      </div>
      <div className='flex h-[200px] items-end gap-1 overflow-x-auto'>
        {data.slice(-14).map((stat, index) => (
          <div key={index} className='flex min-w-[40px] flex-1 flex-col items-center gap-0.5'>
            <div className='flex w-full items-end justify-center gap-0.5' style={{ height: '160px' }}>
              <div
                className='w-2 rounded-t bg-util-colors-gray-gray-400'
                style={{ height: `${(stat.scraped / maxValue) * 160}px` }}
              />
              <div
                className='w-2 rounded-t bg-util-colors-blue-blue-400'
                style={{ height: `${(stat.followed / maxValue) * 160}px` }}
              />
              <div
                className='w-2 rounded-t bg-util-colors-orange-orange-400'
                style={{ height: `${(stat.dm_sent / maxValue) * 160}px` }}
              />
              <div
                className='w-2 rounded-t bg-util-colors-green-green-500'
                style={{ height: `${(stat.converted / maxValue) * 160}px` }}
              />
            </div>
            <div className='text-[10px] text-text-quaternary'>
              {new Date(stat.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Task Summary Card
// =============================================================================

type TaskSummary = {
  total_tasks: number
  completed: number
  running: number
  failed: number
  total_processed: number
  total_success: number
  success_rate: number
}

const TaskSummaryCard: FC<{ data: TaskSummary }> = ({ data }) => {
  const { t } = useTranslation()

  return (
    <div className='rounded-xl border border-divider-subtle bg-components-panel-bg p-5'>
      <h3 className='mb-4 font-medium text-text-secondary'>{t('leads.analytics.taskSummary.title')}</h3>
      <div className='grid grid-cols-2 gap-4'>
        <div>
          <div className='text-2xl font-semibold text-text-primary'>{data.total_tasks}</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.taskSummary.totalTasks')}</div>
        </div>
        <div>
          <div className='text-2xl font-semibold text-util-colors-green-green-600'>{data.completed}</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.taskSummary.completed')}</div>
        </div>
        <div>
          <div className='text-2xl font-semibold text-util-colors-blue-blue-600'>{data.running}</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.taskSummary.running')}</div>
        </div>
        <div>
          <div className='text-2xl font-semibold text-util-colors-red-red-600'>{data.failed}</div>
          <div className='text-xs text-text-tertiary'>{t('leads.analytics.taskSummary.failed')}</div>
        </div>
      </div>
      <div className='mt-4 border-t border-divider-subtle pt-4'>
        <div className='flex items-center justify-between'>
          <span className='text-sm text-text-tertiary'>{t('leads.analytics.taskSummary.successRate')}</span>
          <span className='text-lg font-semibold text-text-secondary'>{data.success_rate}%</span>
        </div>
        <div className='mt-2 h-2 overflow-hidden rounded-full bg-background-default'>
          <div
            className='h-full bg-util-colors-green-green-500'
            style={{ width: `${data.success_rate}%` }}
          />
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Analytics Page
// =============================================================================

const AnalyticsPage: FC = () => {
  const { t } = useTranslation()
  const router = useRouter()
  useDocumentTitle(t('leads.analytics.title'))

  const [activeTab, setActiveTab] = useState('overview')
  const [days, setDays] = useState(30)

  const { data: funnelData, isLoading: funnelLoading, refetch: refetchFunnel } = useAnalyticsFunnel()
  const { data: kolData, isLoading: kolLoading } = useAnalyticsKOLPerformance()
  const { data: dailyData, isLoading: dailyLoading } = useAnalyticsDailyStats(days)
  const { data: taskData, isLoading: taskLoading } = useAnalyticsTaskSummary()

  const isLoading = funnelLoading || kolLoading || dailyLoading || taskLoading

  const tabs = [
    { value: 'overview', text: t('leads.analytics.tabs.overview') },
    { value: 'kol', text: t('leads.analytics.tabs.kolPerformance') },
    { value: 'trends', text: t('leads.analytics.tabs.trends') },
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
          <h1 className='text-xl font-semibold text-text-primary'>{t('leads.analytics.title')}</h1>
        </div>
        <div className='flex items-center gap-2'>
          <div className='flex items-center gap-2 rounded-lg border border-divider-subtle bg-components-panel-bg px-3 py-1.5'>
            <RiFilter3Line className='h-4 w-4 text-text-tertiary' />
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className='bg-transparent text-sm text-text-secondary focus:outline-none'
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <Button variant='secondary' onClick={() => refetchFunnel()}>
            <RiRefreshLine className='mr-1 h-4 w-4' />
            {t('common.operation.refresh')}
          </Button>
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
      <div className='space-y-6 px-12 pb-8'>
        {activeTab === 'overview' && (
          <>
            <div className='grid grid-cols-1 gap-6 lg:grid-cols-3'>
              <div className='lg:col-span-2'>
                {funnelData && <FunnelChart data={funnelData} />}
              </div>
              <div>
                {taskData && <TaskSummaryCard data={taskData} />}
              </div>
            </div>
            {dailyData?.data && <DailyStatsChart data={dailyData.data} />}
          </>
        )}

        {activeTab === 'kol' && kolData?.data && (
          <KOLPerformanceTable data={kolData.data} />
        )}

        {activeTab === 'trends' && dailyData?.data && (
          <DailyStatsChart data={dailyData.data} />
        )}
      </div>
    </div>
  )
}

export default AnalyticsPage
