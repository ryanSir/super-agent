/**
 * 对话消息组件
 *
 * 用户消息：右对齐气泡 + 右侧头像
 * AI 消息：左侧头像 + 内容区域
 */

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { USER_AVATAR, AI_AVATAR } from '../assets/avatars'

type ChatMessageProps = {
  content: string
  role?: 'user' | 'assistant' | 'system'
  isStreaming?: boolean
  timestamp?: string
}

function formatTime(iso?: string): string {
  const d = iso ? new Date(iso) : new Date()
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function ChatMessage({ content, role = 'assistant', isStreaming = false, timestamp }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (role === 'user') {
    return (
      <div className="chat-message chat-message-user">
        <div className="user-bubble-wrap">
          <div className="user-bubble-meta">
            <button className={`msg-copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopy} title="复制">
              {copied ? '✓' : '⎘'}
            </button>
            <span className="message-timestamp">{formatTime(timestamp)}</span>
          </div>
          <div className="user-bubble">{content}</div>
        </div>
        <img src={USER_AVATAR} alt="用户头像" className="message-avatar" />
      </div>
    )
  }

  return (
    <div className="chat-message chat-message-assistant">
      <img src={AI_AVATAR} alt="AI头像" className="message-avatar" />
      <div className="assistant-content-wrap">
        <div className="message-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          {isStreaming && <span className="cursor-blink">▊</span>}
        </div>
        <span className="message-timestamp">{formatTime(timestamp)}</span>
      </div>
    </div>
  )
}

export default ChatMessage
