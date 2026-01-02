'use client'
import type { FC } from 'react'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiAddLine,
  RiDeleteBinLine,
  RiDownloadLine,
  RiEditLine,
  RiExternalLinkLine,
  RiHeartPulseLine,
  RiRefreshLine,
  RiUploadLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import TabSliderNew from '@/app/components/base/tab-slider-new'
import Modal from '@/app/components/base/modal'
import Toast from '@/app/components/base/toast'
import Loading from '@/app/components/base/loading'
import Confirm from '@/app/components/base/confirm'
import Pagination from '@/app/components/base/pagination'
import LeadsNav from '../components/leads-nav'
import {
  useCreateSubAccount,
  useCreateTargetKOL,
  useDeleteSubAccount,
  useDeleteTargetKOL,
  useHealthCheckSubAccount,
  useImportSubAccounts,
  useScrapeFollowers,
  useScraperStatus,
  useSubAccountList,
  useTargetKOLList,
  useUpdateTargetKOL,
} from '@/service/use-leads'
import type { SubAccount, TargetKOL } from '@/service/use-leads'

// =============================================================================
// Target KOL Form
// =============================================================================

type KOLFormProps = {
  onSubmit: (data: Partial<TargetKOL>) => void
  onCancel: () => void
  isLoading: boolean
  initialData?: TargetKOL
}

const KOLForm: FC<KOLFormProps> = ({ onSubmit, onCancel, isLoading, initialData }) => {
  const { t } = useTranslation()
  const [platform, setPlatform] = useState<'x' | 'instagram'>(initialData?.platform || 'x')
  const [username, setUsername] = useState(initialData?.username || '')
  const [displayName, setDisplayName] = useState(initialData?.display_name || '')
  const [profileUrl, setProfileUrl] = useState(initialData?.profile_url || '')
  const [followerCount, setFollowerCount] = useState(initialData?.follower_count?.toString() || '')
  const [niche, setNiche] = useState(initialData?.niche || '')
  const [region, setRegion] = useState(initialData?.region || '')

  const handleSubmit = () => {
    if (!username.trim()) {
      Toast.notify({ type: 'error', message: t('leads.outreach.kol.usernameRequired') })
      return
    }
    onSubmit({
      platform,
      username: username.trim(),
      display_name: displayName.trim() || undefined,
      profile_url: profileUrl.trim() || undefined,
      follower_count: followerCount ? parseInt(followerCount, 10) : undefined,
      niche: niche.trim() || undefined,
      region: region.trim() || undefined,
    })
  }

  return (
    <div className='space-y-4 p-6'>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.platform')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <select
          value={platform}
          onChange={e => setPlatform(e.target.value as 'x' | 'instagram')}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          disabled={!!initialData}
        >
          <option value='x'>X (Twitter)</option>
          <option value='instagram'>Instagram</option>
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.username')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <Input
          value={username}
          onChange={e => setUsername(e.target.value)}
          placeholder='@username'
          disabled={!!initialData}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.displayName')}
        </label>
        <Input
          value={displayName}
          onChange={e => setDisplayName(e.target.value)}
          placeholder={t('leads.outreach.kol.displayNamePlaceholder')}
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.followers')}
        </label>
        <Input
          type='number'
          value={followerCount}
          onChange={e => setFollowerCount(e.target.value)}
          placeholder='50000'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.profileUrl')}
        </label>
        <Input
          value={profileUrl}
          onChange={e => setProfileUrl(e.target.value)}
          placeholder='https://...'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.niche')}
        </label>
        <select
          value={niche}
          onChange={e => setNiche(e.target.value)}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value=''>{t('leads.outreach.kol.selectNiche')}</option>
          <option value='stocks'>Stocks</option>
          <option value='crypto'>Crypto</option>
          <option value='forex'>Forex</option>
          <option value='finance'>Finance</option>
          <option value='tech'>Tech</option>
          <option value='lifestyle'>Lifestyle</option>
          <option value='travel'>Travel</option>
          <option value='fashion'>Fashion</option>
          <option value='general'>General</option>
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.kol.region')}
        </label>
        <Input
          value={region}
          onChange={e => setRegion(e.target.value)}
          placeholder='US, EU, APAC...'
        />
      </div>
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>
          {t('common.operation.cancel')}
        </Button>
        <Button variant='primary' onClick={handleSubmit} loading={isLoading}>
          {initialData ? t('common.operation.save') : t('common.operation.create')}
        </Button>
      </div>
    </div>
  )
}

// =============================================================================
// Sub Account Form
// =============================================================================

type AccountFormProps = {
  onSubmit: (data: Partial<SubAccount> & { password?: string }) => void
  onCancel: () => void
  isLoading: boolean
  kols: TargetKOL[]
}

const AccountForm: FC<AccountFormProps> = ({ onSubmit, onCancel, isLoading, kols }) => {
  const { t } = useTranslation()
  const [platform, setPlatform] = useState<'x' | 'instagram'>('x')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [targetKolId, setTargetKolId] = useState('')

  const handleSubmit = () => {
    if (!username.trim()) {
      Toast.notify({ type: 'error', message: t('leads.outreach.account.usernameRequired') })
      return
    }
    onSubmit({
      platform,
      username: username.trim(),
      email: email.trim() || undefined,
      password: password || undefined,
      target_kol_id: targetKolId || undefined,
    })
  }

  return (
    <div className='space-y-4 p-6'>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.account.platform')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <select
          value={platform}
          onChange={e => setPlatform(e.target.value as 'x' | 'instagram')}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value='x'>X (Twitter)</option>
          <option value='instagram'>Instagram</option>
        </select>
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.account.username')} <span className='text-util-colors-red-red-600'>*</span>
        </label>
        <Input
          value={username}
          onChange={e => setUsername(e.target.value)}
          placeholder='@username'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.account.email')}
        </label>
        <Input
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder='email@example.com'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.account.password')}
        </label>
        <Input
          type='password'
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder='••••••••'
        />
      </div>
      <div>
        <label className='mb-1 block text-sm font-medium text-text-secondary'>
          {t('leads.outreach.account.assignKol')}
        </label>
        <select
          value={targetKolId}
          onChange={e => setTargetKolId(e.target.value)}
          className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
        >
          <option value=''>{t('leads.outreach.account.noAssignment')}</option>
          {kols.map(kol => (
            <option key={kol.id} value={kol.id}>
              @{kol.username} ({kol.platform})
            </option>
          ))}
        </select>
      </div>
      <div className='flex justify-end gap-2 pt-4'>
        <Button variant='secondary' onClick={onCancel}>
          {t('common.operation.cancel')}
        </Button>
        <Button variant='primary' onClick={handleSubmit} loading={isLoading}>
          {t('common.operation.create')}
        </Button>
      </div>
    </div>
  )
}

// =============================================================================
// Import Modal
// =============================================================================

type ImportModalProps = {
  isShow: boolean
  onClose: () => void
  onImport: (platform: string, csvContent: string, targetKolId?: string) => void
  isLoading: boolean
  kols: TargetKOL[]
}

const ImportModal: FC<ImportModalProps> = ({ isShow, onClose, onImport, isLoading, kols }) => {
  const { t } = useTranslation()
  const [platform, setPlatform] = useState<'x' | 'instagram'>('x')
  const [csvContent, setCsvContent] = useState('')
  const [targetKolId, setTargetKolId] = useState('')

  const handleImport = () => {
    if (!csvContent.trim()) {
      Toast.notify({ type: 'error', message: t('leads.outreach.import.csvRequired') })
      return
    }
    onImport(platform, csvContent, targetKolId || undefined)
  }

  return (
    <Modal isShow={isShow} onClose={onClose} title={t('leads.outreach.import.title')} className='!max-w-[500px]'>
      <div className='space-y-4 p-6'>
        <div>
          <label className='mb-1 block text-sm font-medium text-text-secondary'>
            {t('leads.outreach.account.platform')}
          </label>
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value as 'x' | 'instagram')}
            className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          >
            <option value='x'>X (Twitter)</option>
            <option value='instagram'>Instagram</option>
          </select>
        </div>
        <div>
          <label className='mb-1 block text-sm font-medium text-text-secondary'>
            {t('leads.outreach.account.assignKol')}
          </label>
          <select
            value={targetKolId}
            onChange={e => setTargetKolId(e.target.value)}
            className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          >
            <option value=''>{t('leads.outreach.account.noAssignment')}</option>
            {kols.map(kol => (
              <option key={kol.id} value={kol.id}>
                @{kol.username} ({kol.platform})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className='mb-1 block text-sm font-medium text-text-secondary'>
            {t('leads.outreach.import.csvContent')}
          </label>
          <textarea
            value={csvContent}
            onChange={e => setCsvContent(e.target.value)}
            placeholder={t('leads.outreach.import.csvPlaceholder')}
            className='h-40 w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          />
          <p className='mt-1 text-xs text-text-tertiary'>{t('leads.outreach.import.csvHelp')}</p>
        </div>
        <div className='flex justify-end gap-2 pt-4'>
          <Button variant='secondary' onClick={onClose}>
            {t('common.operation.cancel')}
          </Button>
          <Button variant='primary' onClick={handleImport} loading={isLoading}>
            <RiUploadLine className='mr-1 h-4 w-4' />
            {t('leads.outreach.import.import')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// =============================================================================
// Status Badge Component
// =============================================================================

const getStatusBadgeClass = (status: string): string => {
  const classes: Record<string, string> = {
    active: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    healthy: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    paused: 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600',
    cooling: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    needs_verification: 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600',
    banned: 'bg-util-colors-red-red-50 text-util-colors-red-red-600',
    archived: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
  }
  return classes[status] || 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600'
}

// =============================================================================
// Main Page Component
// =============================================================================

const OutreachPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.outreach.title'))

  // State
  const [activeTab, setActiveTab] = useState<string>('kols')
  const [page, setPage] = useState(1)
  const [showCreateKOL, setShowCreateKOL] = useState(false)
  const [showCreateAccount, setShowCreateAccount] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [kolToDelete, setKolToDelete] = useState<string | null>(null)
  const [kolToEdit, setKolToEdit] = useState<TargetKOL | null>(null)
  const [accountToDelete, setAccountToDelete] = useState<string | null>(null)

  // Data
  const { data: kolsData, isLoading: kolsLoading, refetch: refetchKols } = useTargetKOLList({ page, limit: 20 })
  const { data: accountsData, isLoading: accountsLoading, refetch: refetchAccounts } = useSubAccountList({ page, limit: 20 })
  const { data: scraperStatus } = useScraperStatus()

  // Mutations
  const createKOL = useCreateTargetKOL()
  const updateKOL = useUpdateTargetKOL()
  const deleteKOL = useDeleteTargetKOL()
  const createAccount = useCreateSubAccount()
  const importAccounts = useImportSubAccounts()
  const deleteAccount = useDeleteSubAccount()
  const healthCheck = useHealthCheckSubAccount()
  const scrapeFollowers = useScrapeFollowers()

  const tabs = [
    { value: 'kols', text: t('leads.outreach.tabs.kols') },
    { value: 'accounts', text: t('leads.outreach.tabs.accounts') },
  ]

  // Handlers
  const handleCreateKOL = useCallback(async (data: Partial<TargetKOL>) => {
    try {
      await createKOL.mutateAsync(data)
      Toast.notify({ type: 'success', message: t('leads.outreach.message.kolCreated') })
      setShowCreateKOL(false)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.createFailed') })
    }
  }, [createKOL, t])

  const handleUpdateKOL = useCallback(async (data: Partial<TargetKOL>) => {
    if (!kolToEdit)
      return
    try {
      await updateKOL.mutateAsync({ id: kolToEdit.id, ...data })
      Toast.notify({ type: 'success', message: t('leads.outreach.message.kolUpdated') })
      setKolToEdit(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.updateFailed') })
    }
  }, [updateKOL, kolToEdit, t])

  const handleDeleteKOL = useCallback(async () => {
    if (!kolToDelete)
      return
    try {
      await deleteKOL.mutateAsync(kolToDelete)
      Toast.notify({ type: 'success', message: t('leads.outreach.message.kolDeleted') })
      setKolToDelete(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.deleteFailed') })
    }
  }, [deleteKOL, kolToDelete, t])

  const handleCreateAccount = useCallback(async (data: Partial<SubAccount> & { password?: string }) => {
    try {
      await createAccount.mutateAsync(data)
      Toast.notify({ type: 'success', message: t('leads.outreach.message.accountCreated') })
      setShowCreateAccount(false)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.createFailed') })
    }
  }, [createAccount, t])

  const handleImportAccounts = useCallback(async (platform: string, csvContent: string, targetKolId?: string) => {
    try {
      const result = await importAccounts.mutateAsync({ platform, csv_content: csvContent, target_kol_id: targetKolId })
      Toast.notify({
        type: 'success',
        message: t('leads.outreach.message.imported', { count: result.imported }),
      })
      setShowImport(false)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.importFailed') })
    }
  }, [importAccounts, t])

  const handleDeleteAccount = useCallback(async () => {
    if (!accountToDelete)
      return
    try {
      await deleteAccount.mutateAsync(accountToDelete)
      Toast.notify({ type: 'success', message: t('leads.outreach.message.accountDeleted') })
      setAccountToDelete(null)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.deleteFailed') })
    }
  }, [deleteAccount, accountToDelete, t])

  const handleHealthCheck = useCallback(async (accountId: string) => {
    try {
      const result = await healthCheck.mutateAsync(accountId)
      Toast.notify({
        type: 'success',
        message: `Status: ${result.previous_status} → ${result.current_status}`,
      })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.healthCheckFailed') })
    }
  }, [healthCheck, t])

  const handleScrapeFollowers = useCallback(async (kolId: string) => {
    if (!scraperStatus?.configured) {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.scraperNotConfigured') })
      return
    }
    try {
      const result = await scrapeFollowers.mutateAsync({ kolId, maxFollowers: 1000 })
      Toast.notify({
        type: 'success',
        message: t('leads.outreach.message.followerScraped', { count: result.created_count }),
      })
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.outreach.message.scrapeFailed') })
    }
  }, [scraperStatus, scrapeFollowers, t])

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <LeadsNav />
      {/* Header */}
      <div className='flex flex-wrap items-center justify-between gap-y-2 bg-background-body px-12 pb-5 pt-4'>
        <div className='flex items-center gap-4'>
          <TabSliderNew value={activeTab} onChange={setActiveTab} options={tabs} />
          {scraperStatus && (
            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs ${scraperStatus.configured ? 'bg-util-colors-green-green-50 text-util-colors-green-green-600' : 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600'}`}>
              {scraperStatus.configured ? t('leads.outreach.scraper.configured') : t('leads.outreach.scraper.notConfigured')}
            </span>
          )}
        </div>
        <div className='flex items-center gap-2'>
          {activeTab === 'kols' && (
            <>
              <Button variant='secondary' onClick={() => refetchKols()}>
                <RiRefreshLine className='h-4 w-4' />
              </Button>
              <Button variant='primary' onClick={() => setShowCreateKOL(true)}>
                <RiAddLine className='mr-1 h-4 w-4' />
                {t('leads.outreach.kol.add')}
              </Button>
            </>
          )}
          {activeTab === 'accounts' && (
            <>
              <Button variant='secondary' onClick={() => setShowImport(true)}>
                <RiUploadLine className='mr-1 h-4 w-4' />
                {t('leads.outreach.import.title')}
              </Button>
              <Button variant='secondary' onClick={() => refetchAccounts()}>
                <RiRefreshLine className='h-4 w-4' />
              </Button>
              <Button variant='primary' onClick={() => setShowCreateAccount(true)}>
                <RiAddLine className='mr-1 h-4 w-4' />
                {t('leads.outreach.account.add')}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className='px-12 pb-6'>
        {/* KOLs Tab */}
        {activeTab === 'kols' && (
          <>
            {kolsLoading
              ? (
                <div className='flex h-[200px] items-center justify-center'>
                  <Loading type='area' />
                </div>
              )
              : (
                <div className='grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3'>
                  {kolsData?.data?.map((kol: TargetKOL) => (
                    <div
                      key={kol.id}
                      className='rounded-xl border border-divider-subtle bg-components-panel-bg p-4 transition-shadow hover:shadow-sm'
                    >
                      <div className='mb-3 flex items-start justify-between'>
                        <div className='flex items-center gap-3'>
                          <div className='flex h-10 w-10 items-center justify-center rounded-full bg-util-colors-blue-blue-50 text-lg'>
                            {kol.platform === 'x' ? '𝕏' : '📸'}
                          </div>
                          <div>
                            <h3 className='font-medium text-text-secondary'>@{kol.username}</h3>
                            {kol.display_name && (
                              <p className='text-sm text-text-tertiary'>{kol.display_name}</p>
                            )}
                          </div>
                        </div>
                        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusBadgeClass(kol.status)}`}>
                          {t(`leads.outreach.status.${kol.status}`)}
                        </span>
                      </div>
                      <div className='mb-3 grid grid-cols-2 gap-2 text-sm'>
                        <div>
                          <span className='text-text-tertiary'>{t('leads.outreach.kol.followers')}:</span>
                          <span className='ml-1 text-text-secondary'>{kol.follower_count.toLocaleString()}</span>
                        </div>
                        {kol.niche && (
                          <div>
                            <span className='text-text-tertiary'>{t('leads.outreach.kol.niche')}:</span>
                            <span className='ml-1 text-text-secondary'>{kol.niche}</span>
                          </div>
                        )}
                        {kol.region && (
                          <div>
                            <span className='text-text-tertiary'>{t('leads.outreach.kol.region')}:</span>
                            <span className='ml-1 text-text-secondary'>{kol.region}</span>
                          </div>
                        )}
                      </div>
                      <div className='flex flex-wrap gap-2'>
                        <Button
                          variant='primary'
                          size='small'
                          onClick={() => handleScrapeFollowers(kol.id)}
                          loading={scrapeFollowers.isPending}
                        >
                          <RiDownloadLine className='mr-1 h-3 w-3' />
                          {t('leads.outreach.kol.scrapeFollowers')}
                        </Button>
                        <Button
                          variant='secondary'
                          size='small'
                          onClick={() => setKolToEdit(kol)}
                          title={t('common.operation.edit')}
                        >
                          <RiEditLine className='h-3 w-3' />
                        </Button>
                        {kol.profile_url && (
                          <Button
                            variant='ghost'
                            size='small'
                            onClick={() => window.open(kol.profile_url, '_blank')}
                          >
                            <RiExternalLinkLine className='h-3 w-3' />
                          </Button>
                        )}
                        <Button
                          variant='ghost'
                          size='small'
                          onClick={() => setKolToDelete(kol.id)}
                        >
                          <RiDeleteBinLine className='h-3 w-3' />
                        </Button>
                      </div>
                    </div>
                  ))}
                  {(!kolsData?.data || kolsData.data.length === 0) && (
                    <div className='col-span-full py-12 text-center'>
                      <p className='text-text-tertiary'>{t('leads.outreach.empty.kols')}</p>
                    </div>
                  )}
                </div>
              )}
            {kolsData && kolsData.total > 20 && (
              <Pagination
                className='mt-4'
                current={page - 1}
                onChange={p => setPage(p + 1)}
                total={kolsData.total}
                limit={20}
              />
            )}
          </>
        )}

        {/* Accounts Tab */}
        {activeTab === 'accounts' && (
          <>
            {accountsLoading
              ? (
                <div className='flex h-[200px] items-center justify-center'>
                  <Loading type='area' />
                </div>
              )
              : (
                <div className='overflow-x-auto rounded-xl border border-divider-subtle bg-components-panel-bg'>
                  <table className='w-full'>
                    <thead>
                      <tr className='border-b border-divider-subtle'>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.outreach.account.username')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.outreach.account.platform')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.outreach.account.status')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.outreach.account.dailyUsage')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.outreach.account.lifetime')}</th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-text-tertiary'>{t('leads.outreach.account.actions')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {accountsData?.data?.map((account: SubAccount) => (
                        <tr key={account.id} className='border-b border-divider-subtle last:border-0'>
                          <td className='px-4 py-3 text-sm text-text-secondary'>@{account.username}</td>
                          <td className='px-4 py-3'>
                            <span className='inline-flex items-center rounded-md bg-util-colors-blue-blue-50 px-2 py-1 text-xs text-util-colors-blue-blue-600'>
                              {account.platform === 'x' ? 'X' : 'Instagram'}
                            </span>
                          </td>
                          <td className='px-4 py-3'>
                            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusBadgeClass(account.status)}`}>
                              {t(`leads.outreach.accountStatus.${account.status}`)}
                            </span>
                          </td>
                          <td className='px-4 py-3 text-sm text-text-tertiary'>
                            {account.daily_follows_used}/{account.daily_limit_follows} F · {account.daily_dms_used}/{account.daily_limit_dms} DM
                          </td>
                          <td className='px-4 py-3 text-sm text-text-tertiary'>
                            {account.lifetime_follows} F · {account.lifetime_dms} DM
                          </td>
                          <td className='px-4 py-3'>
                            <div className='flex items-center gap-1'>
                              <Button
                                variant='ghost'
                                size='small'
                                onClick={() => handleHealthCheck(account.id)}
                                loading={healthCheck.isPending}
                                title={t('leads.outreach.account.healthCheck')}
                              >
                                <RiHeartPulseLine className='h-3 w-3' />
                              </Button>
                              <Button
                                variant='ghost'
                                size='small'
                                onClick={() => setAccountToDelete(account.id)}
                              >
                                <RiDeleteBinLine className='h-3 w-3' />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {(!accountsData?.data || accountsData.data.length === 0) && (
                    <div className='py-12 text-center'>
                      <p className='text-text-tertiary'>{t('leads.outreach.empty.accounts')}</p>
                    </div>
                  )}
                </div>
              )}
            {accountsData && accountsData.total > 20 && (
              <Pagination
                className='mt-4'
                current={page - 1}
                onChange={p => setPage(p + 1)}
                total={accountsData.total}
                limit={20}
              />
            )}
          </>
        )}
      </div>

      {/* Modals */}
      <Modal isShow={showCreateKOL} onClose={() => setShowCreateKOL(false)} title={t('leads.outreach.kol.add')} className='!max-w-[480px]'>
        <KOLForm
          onSubmit={handleCreateKOL}
          onCancel={() => setShowCreateKOL(false)}
          isLoading={createKOL.isPending}
        />
      </Modal>

      {/* Edit KOL Modal */}
      <Modal isShow={!!kolToEdit} onClose={() => setKolToEdit(null)} title={t('leads.outreach.kol.edit')} className='!max-w-[480px]'>
        {kolToEdit && (
          <KOLForm
            onSubmit={handleUpdateKOL}
            onCancel={() => setKolToEdit(null)}
            isLoading={updateKOL.isPending}
            initialData={kolToEdit}
          />
        )}
      </Modal>

      <Modal isShow={showCreateAccount} onClose={() => setShowCreateAccount(false)} title={t('leads.outreach.account.add')} className='!max-w-[480px]'>
        <AccountForm
          onSubmit={handleCreateAccount}
          onCancel={() => setShowCreateAccount(false)}
          isLoading={createAccount.isPending}
          kols={kolsData?.data || []}
        />
      </Modal>

      <ImportModal
        isShow={showImport}
        onClose={() => setShowImport(false)}
        onImport={handleImportAccounts}
        isLoading={importAccounts.isPending}
        kols={kolsData?.data || []}
      />

      <Confirm
        isShow={!!kolToDelete}
        onCancel={() => setKolToDelete(null)}
        onConfirm={handleDeleteKOL}
        title={t('leads.outreach.confirm.deleteKol')}
        content={t('leads.outreach.confirm.deleteKolDesc')}
        type='warning'
      />

      <Confirm
        isShow={!!accountToDelete}
        onCancel={() => setAccountToDelete(null)}
        onConfirm={handleDeleteAccount}
        title={t('leads.outreach.confirm.deleteAccount')}
        content={t('leads.outreach.confirm.deleteAccountDesc')}
        type='warning'
      />
    </div>
  )
}

export default OutreachPage
