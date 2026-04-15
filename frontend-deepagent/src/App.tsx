/**
 * 主应用组件
 *
 * 聊天界面入口，负责：
 * - SSE 连接管理（自动建连、断点续传）
 * - 用户输入处理（文本输入、Skill 提及、快捷问题）
 * - A2UI 事件驱动的 UI 状态更新
 * - 消息历史展示和实时响应渲染
 */

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { createSSEClient, submitQuery, SSEClient } from './engine/SSEClient'
import { handleEvent, createInitialState, UIState } from './engine/MessageHandler'
import ResponseBlock from './components/ResponseBlock'
import ChatMessage from './components/ChatMessage'
import SkillMention, { Skill } from './components/SkillMention'
import { AI_AVATAR } from './assets/avatars'

// localStorage keys
const STORAGE_SESSION_ID = 'super-agent-session-id'
const STORAGE_THEME = 'super-agent-theme'

// 快捷测试问题
const QUICK_QUESTIONS = [
  { label: '🔍 搜索测试', query: '帮我搜索一下 2026 年大语言模型的最新进展' },
  { label: '📄 专利查询', query: '帮我查一下 US10987654B2 在美国和欧洲的当前法律状态、维持/续费情况以及预计到期时间' },
  { label: '📊 数据分析', query: '查询苏州最近一周的天气情况，并生成精美的温度折线趋势图' },
  { label: '💻 代码生成', query: '用 Python 写一个 hello world，并打印出来' },
  { label: '📑 PPT 生成', query: '帮我生成一份关于人工智能发展趋势的 PPT' },
  { label: '🔗 多步任务', query: '先搜索 Transformer 架构的最新论文，然后总结核心观点，最后生成一份简报' },
]

// 品牌 Logo SVG
const BRAND_LOGO = (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#0ea5e9"/>
        <stop offset="100%" stopColor="#6366f1"/>
      </linearGradient>
    </defs>
    <circle cx="24" cy="24" r="22" fill="url(#logoGrad)" opacity="0.15"/>
    <circle cx="24" cy="24" r="22" stroke="url(#logoGrad)" strokeWidth="2" fill="none"/>
    <circle cx="24" cy="18" r="5" fill="url(#logoGrad)"/>
    <path d="M12 38 Q12 28 24 28 Q36 28 36 38" fill="url(#logoGrad)"/>
    <circle cx="16" cy="24" r="2.5" fill="url(#logoGrad)" opacity="0.5"/>
    <circle cx="32" cy="24" r="2.5" fill="url(#logoGrad)" opacity="0.5"/>
  </svg>
)

function App() {
  const [sessionId] = useState(() => {
    const stored = localStorage.getItem(STORAGE_SESSION_ID)
    if (stored) return stored
    const newId = `sess-${Date.now().toString(36)}`
    localStorage.setItem(STORAGE_SESSION_ID, newId)
    return newId
  })

  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem(STORAGE_THEME) as 'dark' | 'light') || 'dark'
  })

  const [state, setState] = useState<UIState>(() => createInitialState(sessionId))
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<string>('auto')
  const sseRef = useRef<SSEClient | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Skill mention 状态
  const [skills, setSkills] = useState<Skill[]>([])
  const [mentionOpen, setMentionOpen] = useState(false)
  const [mentionFilter, setMentionFilter] = useState('')
  const [mentionIndex, setMentionIndex] = useState(0)

  // 拉取 skill 列表
  useEffect(() => {
    const isDev = import.meta.env.DEV
    const host = isDev ? 'http://localhost:9001' : ''
    fetch(`${host}/api/agent/skills`)
      .then((r) => r.json())
      .then((data) => {
        if (data.skills) setSkills(data.skills)
      })
      .catch(() => {})
  }, [])

  // 同步主题到 html 元素
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(STORAGE_THEME, theme)
  }, [theme])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [state.messages, state.currentResponse])

  // 页面加载时自动连接 SSE
  useEffect(() => {
    const client = createSSEClient(
      sessionId,
      (event) => {
        setState((prev) => handleEvent(prev, event))
      },
      () => {
        setState((prev) => ({ ...prev, isConnected: false }))
      },
    )
    sseRef.current = client
    setState((prev) => ({ ...prev, isConnected: true }))

    return () => { client.close() }
  }, [sessionId])

  // textarea 高度自适应
  const adjustTextareaHeight = useCallback((el: HTMLTextAreaElement) => {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  // 发送查询
  const sendQuery = useCallback(
    async (query: string) => {
      if (!query.trim() || state.isProcessing) return

      setState((prev) => ({
        ...prev,
        isProcessing: true,
        error: null,
        messages: [
          ...prev.messages,
          {
            id: `msg-${Date.now()}`,
            type: 'user' as const,
            content: query,
            timestamp: new Date().toISOString(),
          },
        ],
      }))
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }

      try {
        await submitQuery(sessionId, query, mode)
      } catch {
        setState((prev) => ({
          ...prev,
          isProcessing: false,
          error: '请求发送失败，请重试',
        }))
      }
    },
    [sessionId, state.isProcessing, mode],
  )

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      sendQuery(input)
    },
    [input, sendQuery],
  )

  const selectSkill = useCallback(
    (skill: Skill) => {
      const slashIdx = input.lastIndexOf('/')
      const newInput = input.slice(0, slashIdx) + skill.name + ' '
      setInput(newInput)
      setMentionOpen(false)
      setMentionFilter('')
      setMentionIndex(0)
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus()
          adjustTextareaHeight(textareaRef.current)
        }
      }, 0)
    },
    [input, adjustTextareaHeight],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (mentionOpen) {
        const filtered = skills.filter(
          (s) =>
            mentionFilter === '' ||
            s.name.toLowerCase().includes(mentionFilter.toLowerCase()) ||
            s.description.toLowerCase().includes(mentionFilter.toLowerCase()),
        )
        if (e.key === 'ArrowDown') {
          e.preventDefault()
          setMentionIndex((i) => Math.min(i + 1, filtered.length - 1))
          return
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault()
          setMentionIndex((i) => Math.max(i - 1, 0))
          return
        }
        if (e.key === 'Enter' && filtered[mentionIndex]) {
          e.preventDefault()
          selectSkill(filtered[mentionIndex])
          return
        }
        if (e.key === 'Escape') {
          setMentionOpen(false)
          return
        }
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        sendQuery(input)
      }
    },
    [input, sendQuery, mentionOpen, mentionFilter, mentionIndex, skills],
  )

  const handleInput = useCallback(
    (e: React.FormEvent<HTMLTextAreaElement>) => {
      adjustTextareaHeight(e.currentTarget)
    },
    [adjustTextareaHeight],
  )

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value
      setInput(val)
      const slashIdx = val.lastIndexOf('/')
      if (slashIdx >= 0 && (slashIdx === 0 || val[slashIdx - 1] === ' ' || val[slashIdx - 1] === '\n')) {
        const after = val.slice(slashIdx + 1)
        if (!after.includes(' ')) {
          setMentionFilter(after)
          setMentionOpen(true)
          setMentionIndex(0)
          return
        }
      }
      setMentionOpen(false)
    },
    [],
  )

  const handleNewSession = useCallback(() => {
    localStorage.removeItem(STORAGE_SESSION_ID)
    window.location.reload()
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Super Agent</h1>
        <span className="badge">{state.isConnected ? '已连接' : '重连中...'}</span>
        <div className="header-actions">
          <button onClick={toggleTheme} className="theme-toggle-btn" title={theme === 'dark' ? '切换亮色' : '切换暗色'}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button onClick={handleNewSession} className="new-session-btn">新会话</button>
        </div>
      </header>

      <main className="app-main">
        {/* 空状态欢迎区 */}
        {state.messages.length === 0 && !state.currentResponse && (
          <div className="welcome-state">
            <div className="welcome-logo">{BRAND_LOGO}</div>
            <h2 className="welcome-title">有什么我可以帮你的？</h2>
            <p className="welcome-subtitle">AI 驱动的智能助手，支持搜索、分析、代码生成等多种任务</p>
            <div className="quick-questions-grid">
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q.label}
                  className="quick-question-btn"
                  onClick={() => sendQuery(q.query)}
                  disabled={state.isProcessing}
                >
                  <span className="quick-question-label">{q.label}</span>
                  <span className="quick-question-text">{q.query}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 消息历史 */}
        {state.messages.map((msg) => (
          <div key={msg.id} className={`message-row message-row-${msg.type}`}>
            {msg.type === 'user' ? (
              <ChatMessage content={msg.content} role="user" timestamp={msg.timestamp} />
            ) : (
              <div className="assistant-row">
              <img src={AI_AVATAR} alt="AI" className="message-avatar" />
              <ResponseBlock response={msg.response} />
            </div>
            )}
          </div>
        ))}

        {/* 当前正在构建的回答 */}
        {state.currentResponse && (
          <div className="message-row message-row-assistant">
            <div className="assistant-row">
              <img src={AI_AVATAR} alt="AI" className="message-avatar" />
              <ResponseBlock response={state.currentResponse} isLive />
            </div>
          </div>
        )}

        {/* 错误提示 */}
        {state.error && (
          <div className="error-banner">{state.error}</div>
        )}

        <div ref={messagesEndRef} />
      </main>

      <footer className="app-footer">
        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-wrapper">
            {mentionOpen && (
              <SkillMention
                skills={skills}
                filter={mentionFilter}
                selectedIndex={mentionIndex}
                onSelect={selectSkill}
              />
            )}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              onInput={handleInput}
              placeholder="输入你的请求，/ 选择 Skill..."
              disabled={state.isProcessing}
              className="input-field"
              rows={1}
            />
          </div>
          <button
            type="submit"
            disabled={state.isProcessing || !input.trim()}
            className="submit-btn"
          >
            {state.isProcessing ? '处理中...' : '发送'}
          </button>
        </form>
        <div className="footer-bar">
          <div className="mode-selector">
            <span className="mode-label">模式</span>
            {[
              { value: 'auto', label: '自动', icon: '⚡' },
              { value: 'direct', label: '直接', icon: '↗' },
              { value: 'plan_and_execute', label: '规划', icon: '📋' },
              { value: 'sub_agent', label: '协作', icon: '👥' },
            ].map((m) => (
              <button
                key={m.value}
                type="button"
                className={`mode-pill${mode === m.value ? ' mode-pill-active' : ''}`}
                onClick={() => setMode(m.value)}
                disabled={state.isProcessing}
                title={
                  m.value === 'auto' ? 'AI 自动判断最佳执行模式' :
                  m.value === 'direct' ? '简单任务，直接回答' :
                  m.value === 'plan_and_execute' ? '复杂任务，先规划再执行' :
                  '多角色协作完成复杂任务'
                }
              >
                <span className="mode-pill-icon">{m.icon}</span>
                {m.label}
              </button>
            ))}
          </div>
          <span className="input-hint">Enter 发送 · Shift+Enter 换行 · / 选择 Skill</span>
        </div>
      </footer>
    </div>
  )
}

export default App
