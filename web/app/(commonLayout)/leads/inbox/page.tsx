'use client'
import type { FC } from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiCheckLine,
  RiCloseLine,
  RiRefreshLine,
  RiRobotLine,
  RiSendPlaneLine,
  RiUserLine,
} from '@remixicon/react'
import useDocumentTitle from '@/hooks/use-document-title'
import Button from '@/app/components/base/button'
import Loading from '@/app/components/base/loading'
import Toast from '@/app/components/base/toast'
import {
  useConversation,
  useConversationList,
  useGenerateAIReply,
  useSendMessage,
  useUpdateConversationStatus,
} from '@/service/use-leads'
import type { OutreachConversation, OutreachMessage } from '@/service/use-leads'

// =============================================================================
// Status Badge
// =============================================================================

const getStatusBadgeClass = (status: string): string => {
  const classes: Record<string, string> = {
    ai_handling: 'bg-util-colors-blue-blue-50 text-util-colors-blue-blue-600',
    needs_human: 'bg-util-colors-orange-orange-50 text-util-colors-orange-orange-600',
    human_handling: 'bg-util-colors-indigo-indigo-50 text-util-colors-indigo-indigo-600',
    paused: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
    converted: 'bg-util-colors-green-green-50 text-util-colors-green-green-600',
    closed: 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600',
  }
  return classes[status] || 'bg-util-colors-gray-gray-50 text-util-colors-gray-gray-600'
}

// =============================================================================
// Conversation List Item
// =============================================================================

type ConversationItemProps = {
  conversation: OutreachConversation
  isSelected: boolean
  onClick: () => void
}

const ConversationItem: FC<ConversationItemProps> = ({ conversation, isSelected, onClick }) => {
  const { t } = useTranslation()

  return (
    <div
      onClick={onClick}
      className={`cursor-pointer border-b border-divider-subtle p-4 transition-colors hover:bg-background-default-hover ${isSelected ? 'bg-background-default-hover' : ''}`}
    >
      <div className='flex items-start justify-between'>
        <div className='flex items-center gap-3'>
          <div className='flex h-10 w-10 items-center justify-center rounded-full bg-util-colors-blue-blue-50 text-sm'>
            {conversation.follower?.avatar_url
              ? <img src={conversation.follower.avatar_url} alt='' className='h-full w-full rounded-full object-cover' />
              : conversation.platform === 'x' ? '𝕏' : '📸'}
          </div>
          <div>
            <h4 className='font-medium text-text-secondary'>
              @{conversation.follower?.username || 'unknown'}
            </h4>
            <p className='text-xs text-text-tertiary'>{conversation.platform}</p>
          </div>
        </div>
        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusBadgeClass(conversation.status)}`}>
          {t(`leads.inbox.status.${conversation.status}`)}
        </span>
      </div>
      <div className='mt-2 flex items-center gap-4 text-xs text-text-tertiary'>
        <span>{conversation.total_messages} messages</span>
        <span>{conversation.ai_turns} AI · {conversation.human_messages} Human</span>
        {conversation.conversion_score !== undefined && conversation.conversion_score > 0 && (
          <span className='text-util-colors-green-green-600'>
            {conversation.conversion_score}% conversion
          </span>
        )}
      </div>
      {conversation.human_reason && (
        <p className='mt-2 truncate text-xs text-util-colors-orange-orange-600'>
          ⚠️ {conversation.human_reason}
        </p>
      )}
      {conversation.last_message_at && (
        <p className='mt-1 text-xs text-text-quaternary'>
          {new Date(conversation.last_message_at).toLocaleString()}
        </p>
      )}
    </div>
  )
}

// =============================================================================
// Message Bubble
// =============================================================================

type MessageBubbleProps = {
  message: OutreachMessage
}

const MessageBubble: FC<MessageBubbleProps> = ({ message }) => {
  const isOutbound = message.direction === 'outbound'

  return (
    <div className={`flex ${isOutbound ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[70%] rounded-lg px-4 py-2 ${
        isOutbound
          ? message.sender_type === 'ai'
            ? 'text-util-colors-blue-blue-800 bg-util-colors-blue-blue-100'
            : 'text-util-colors-indigo-indigo-800 bg-util-colors-indigo-indigo-100'
          : 'bg-components-panel-bg text-text-secondary'
      }`}
      >
        <div className='mb-1 flex items-center gap-2 text-xs opacity-70'>
          {isOutbound
            ? message.sender_type === 'ai'
              ? <><RiRobotLine className='h-3 w-3' /> AI</>
              : <><RiUserLine className='h-3 w-3' /> Human</>
            : 'Follower'}
          <span>·</span>
          <span>{new Date(message.created_at).toLocaleTimeString()}</span>
        </div>
        <p className='whitespace-pre-wrap text-sm'>{message.content}</p>
        {message.ai_intent && (
          <span className='mt-1 inline-block rounded bg-black/10 px-1.5 py-0.5 text-xs'>
            {message.ai_intent}
          </span>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Conversation Detail
// =============================================================================

type ConversationDetailProps = {
  conversationId: string
  onStatusChange: () => void
}

const ConversationDetail: FC<ConversationDetailProps> = ({ conversationId, onStatusChange }) => {
  const { t } = useTranslation()
  const [newMessage, setNewMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { data: conversation, isLoading, refetch } = useConversation(conversationId)
  const sendMessage = useSendMessage()
  const generateAI = useGenerateAIReply()
  const updateStatus = useUpdateConversationStatus()

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages])

  const handleSend = useCallback(async () => {
    if (!newMessage.trim())
      return
    try {
      await sendMessage.mutateAsync({
        conversationId,
        content: newMessage.trim(),
        senderType: 'human',
      })
      setNewMessage('')
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.inbox.message.sendFailed') })
    }
  }, [sendMessage, conversationId, newMessage, refetch, t])

  const handleGenerateAI = useCallback(async () => {
    try {
      const result = await generateAI.mutateAsync(conversationId)
      Toast.notify({
        type: 'success',
        message: `AI suggestion (${result.intent}): ${result.content.substring(0, 50)}...`,
      })
      setNewMessage(result.content)
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.inbox.message.generateFailed') })
    }
  }, [generateAI, conversationId, t])

  const handleTakeover = useCallback(async () => {
    try {
      await updateStatus.mutateAsync({ id: conversationId, status: 'human_handling' })
      Toast.notify({ type: 'success', message: t('leads.inbox.message.takenOver') })
      onStatusChange()
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.inbox.message.takeoverFailed') })
    }
  }, [updateStatus, conversationId, onStatusChange, refetch, t])

  const handleClose = useCallback(async () => {
    try {
      await updateStatus.mutateAsync({ id: conversationId, status: 'closed' })
      Toast.notify({ type: 'success', message: t('leads.inbox.message.closed') })
      onStatusChange()
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.inbox.message.closeFailed') })
    }
  }, [updateStatus, conversationId, onStatusChange, refetch, t])

  const handleMarkConverted = useCallback(async () => {
    try {
      await updateStatus.mutateAsync({ id: conversationId, status: 'converted' })
      Toast.notify({ type: 'success', message: t('leads.inbox.message.converted') })
      onStatusChange()
      refetch()
    }
    catch {
      Toast.notify({ type: 'error', message: t('leads.inbox.message.convertFailed') })
    }
  }, [updateStatus, conversationId, onStatusChange, refetch, t])

  if (isLoading) {
    return (
      <div className='flex h-full items-center justify-center'>
        <Loading type='area' />
      </div>
    )
  }

  if (!conversation) {
    return (
      <div className='flex h-full items-center justify-center text-text-tertiary'>
        {t('leads.inbox.empty.conversation')}
      </div>
    )
  }

  return (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='flex items-center justify-between border-b border-divider-subtle p-4'>
        <div className='flex items-center gap-3'>
          <div className='flex h-10 w-10 items-center justify-center rounded-full bg-util-colors-blue-blue-50'>
            {conversation.platform === 'x' ? '𝕏' : '📸'}
          </div>
          <div>
            <h3 className='font-medium text-text-secondary'>
              @{conversation.follower?.username}
            </h3>
            <p className='text-xs text-text-tertiary'>
              {conversation.follower?.bio?.substring(0, 60)}...
            </p>
          </div>
        </div>
        <div className='flex items-center gap-2'>
          <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${getStatusBadgeClass(conversation.status)}`}>
            {t(`leads.inbox.status.${conversation.status}`)}
          </span>
          {conversation.status === 'needs_human' && (
            <Button variant='primary' size='small' onClick={handleTakeover}>
              {t('leads.inbox.action.takeover')}
            </Button>
          )}
          {conversation.status !== 'converted' && conversation.status !== 'closed' && (
            <>
              <Button variant='secondary' size='small' onClick={handleMarkConverted}>
                <RiCheckLine className='mr-1 h-3 w-3' />
                {t('leads.inbox.action.markConverted')}
              </Button>
              <Button variant='ghost' size='small' onClick={handleClose}>
                <RiCloseLine className='h-3 w-3' />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className='flex-1 overflow-y-auto p-4'>
        {conversation.messages?.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {conversation.status !== 'closed' && conversation.status !== 'converted' && (
        <div className='border-t border-divider-subtle p-4'>
          <div className='flex gap-2'>
            <textarea
              value={newMessage}
              onChange={e => setNewMessage(e.target.value)}
              placeholder={t('leads.inbox.input.placeholder')}
              className='flex-1 resize-none rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary focus:outline-none'
              rows={2}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />
            <div className='flex flex-col gap-1'>
              <Button
                variant='primary'
                size='small'
                onClick={handleSend}
                loading={sendMessage.isPending}
                disabled={!newMessage.trim()}
              >
                <RiSendPlaneLine className='h-4 w-4' />
              </Button>
              <Button
                variant='secondary'
                size='small'
                onClick={handleGenerateAI}
                loading={generateAI.isPending}
                title={t('leads.inbox.action.generateAI')}
              >
                <RiRobotLine className='h-4 w-4' />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Main Page
// =============================================================================

const InboxPage: FC = () => {
  const { t } = useTranslation()
  useDocumentTitle(t('leads.inbox.title'))

  const [statusFilter, setStatusFilter] = useState<string>('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [hasNeedsHuman, setHasNeedsHuman] = useState(false)

  const { data: conversations, isLoading, refetch } = useConversationList(
    { status: statusFilter || undefined, limit: 50 },
    { refetchInterval: hasNeedsHuman ? 5000 : 30000 },
  )

  // Check if any conversation needs human attention
  useEffect(() => {
    const needsHuman = conversations?.data?.some(c => c.status === 'needs_human') ?? false
    setHasNeedsHuman(needsHuman)
  }, [conversations])

  const statusOptions = [
    { value: '', label: t('leads.inbox.filter.all') },
    { value: 'needs_human', label: t('leads.inbox.filter.needsHuman') },
    { value: 'ai_handling', label: t('leads.inbox.filter.aiHandling') },
    { value: 'human_handling', label: t('leads.inbox.filter.humanHandling') },
    { value: 'converted', label: t('leads.inbox.filter.converted') },
    { value: 'closed', label: t('leads.inbox.filter.closed') },
  ]

  const needsHumanCount = conversations?.data?.filter(c => c.status === 'needs_human').length || 0

  return (
    <div className='flex h-[calc(100vh-64px)] bg-background-body'>
      {/* Sidebar - Conversation List */}
      <div className='flex w-[360px] flex-col border-r border-divider-subtle'>
        {/* Header */}
        <div className='flex items-center justify-between border-b border-divider-subtle p-4'>
          <div className='flex items-center gap-2'>
            <h2 className='text-lg font-semibold text-text-primary'>{t('leads.inbox.title')}</h2>
            {needsHumanCount > 0 && (
              <span className='inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-util-colors-red-red-500 px-1.5 text-xs font-medium text-white'>
                {needsHumanCount}
              </span>
            )}
          </div>
          <Button variant='ghost' size='small' onClick={() => refetch()}>
            <RiRefreshLine className='h-4 w-4' />
          </Button>
        </div>

        {/* Filter */}
        <div className='border-b border-divider-subtle p-3'>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className='w-full rounded-lg border border-components-input-border-active bg-components-input-bg-normal px-3 py-2 text-sm text-text-secondary'
          >
            {statusOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* List */}
        <div className='flex-1 overflow-y-auto'>
          {isLoading
            ? (
              <div className='flex h-[200px] items-center justify-center'>
                <Loading type='area' />
              </div>
            )
            : conversations?.data?.length
              ? conversations.data.map(conv => (
                <ConversationItem
                  key={conv.id}
                  conversation={conv}
                  isSelected={selectedId === conv.id}
                  onClick={() => setSelectedId(conv.id)}
                />
              ))
              : (
                <div className='p-8 text-center text-text-tertiary'>
                  {t('leads.inbox.empty.conversations')}
                </div>
              )}
        </div>
      </div>

      {/* Main - Conversation Detail */}
      <div className='flex-1'>
        {selectedId
          ? (
            <ConversationDetail
              conversationId={selectedId}
              onStatusChange={refetch}
            />
          )
          : (
            <div className='flex h-full items-center justify-center text-text-tertiary'>
              {t('leads.inbox.empty.selectConversation')}
            </div>
          )}
      </div>
    </div>
  )
}

export default InboxPage
