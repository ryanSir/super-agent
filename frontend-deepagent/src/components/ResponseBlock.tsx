/**
 * 回答块容器
 *
 * 分层卡片布局：思考过程 → 执行阶段 → 工具调用 → 子 Agent → 最终回答
 */

import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { ResponseState } from '../engine/MessageHandler'
import { renderWidget } from '../engine/ComponentRegistry'
import ThinkingSection from './ThinkingSection'
import StepsTimeline from './StepsTimeline'
import ToolResultCard from './ToolResultCard'
import ProcessProgress, { Phase, PhaseStatus } from './ProcessProgress'
import SubAgentCard from './SubAgentCard'

type ResponseBlockProps = {
  response: ResponseState
  isLive?: boolean
}

const PHASE_LABELS: Record<string, string> = {
  planning: '规划',
  executing: '执行',
}

const ALL_PHASES = ['planning', 'executing']

function buildPhases(processPhases: ResponseState['processPhases']): Phase[] {
  return ALL_PHASES.map((name) => {
    const found = processPhases.find((p) => p.phase === name)
    return {
      name,
      label: PHASE_LABELS[name] || name,
      status: (found?.status ?? 'pending') as PhaseStatus,
    }
  })
}

function CodeBlock({ children, ...props }: React.HTMLAttributes<HTMLPreElement>) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    const code =
      (props as any)['data-code'] ||
      (typeof children === 'string'
        ? children
        : React.Children.toArray(children)
            .map((c: any) => c?.props?.children ?? '')
            .join(''))
    navigator.clipboard.writeText(String(code)).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="code-block-wrap">
      <pre {...props}>{children}</pre>
      <button className={`code-copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopy}>
        {copied ? '已复制' : '复制'}
      </button>
    </div>
  )
}

interface EurekaAgentCard {
  title: string
  desc: string
  url: string
}

const EUREKA_BASE_URL = 'https://stage-eureka.zhihuiya.com'

function parseEurekaAgent(text: string): EurekaAgentCard | null {
  const titleMatch = text.match(/title:\s*(.+)/)
  const descMatch = text.match(/desc:\s*(.+)/)
  const urlMatch = text.match(/url:\s*(\S+)/)
  if (!urlMatch) return null
  const url = urlMatch[1].trim()
  return {
    title: titleMatch?.[1]?.trim() ?? '',
    desc: descMatch?.[1]?.trim() ?? '',
    url: url.startsWith('http') ? url : `${EUREKA_BASE_URL}${url}`,
  }
}

function EurekaAgentCardComp({ title, desc, url }: EurekaAgentCard) {
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="eureka-agent-card">
      <div className="eureka-agent-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M12 2L13.09 8.26L19 6L15.45 11.13L21 13.27L15.09 14.5L17 20L12 16.9L7 20L8.91 14.5L3 13.27L8.55 11.13L5 6L10.91 8.26L12 2Z"
            fill="currentColor"
          />
        </svg>
      </div>
      <div className="eureka-agent-body">
        <div className="eureka-agent-title">{title}</div>
        <div className="eureka-agent-desc">{desc}</div>
        <div className="eureka-agent-link">
          点击进入分析
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{ marginLeft: 4, verticalAlign: 'middle' }}
          >
            <path
              d="M18 13V19C18 20.1 17.1 21 16 21H5C3.9 21 3 20.1 3 19V8C3 6.9 3.9 6 5 6H11"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="M15 3H21V9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M10 14L21 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    </a>
  )
}

function renderAnswer(answer: string): React.ReactNode[] {
  const parts = answer.split(/(<eureka-agent>[\s\S]*?<\/eureka-agent>)/g)
  return parts.map((part, i) => {
    const match = part.match(/^<eureka-agent>([\s\S]*?)<\/eureka-agent>$/)
    if (match) {
      const card = parseEurekaAgent(match[1])
      if (card) return <EurekaAgentCardComp key={i} {...card} />
    }
    if (!part.trim()) return null
    return (
      <ReactMarkdown
        key={i}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{ pre: CodeBlock as any }}
      >
        {part}
      </ReactMarkdown>
    )
  })
}

function ResponseBlock({ response, isLive = false }: ResponseBlockProps) {
  const { thinking, steps, toolResults, widgets, subAgents, processPhases, answer, answerComplete } = response

  const phases = buildPhases(processPhases)
  const hasProcessPhases = processPhases.length > 0
  // 过滤掉 process_update 产生的步骤（已由 ProcessProgress 处理）
  const nonProcessSteps = steps.filter((s) => !s.stepId.startsWith('process-'))

  return (
    <div className="response-block">
      {/* 思考过程 */}
      {(thinking || (isLive && nonProcessSteps.length === 0 && !answer)) && (
        <ThinkingSection content={thinking} isActive={isLive && !answerComplete} />
      )}

      {/* 执行阶段进度 */}
      {hasProcessPhases && (
        <div className="response-card">
          <ProcessProgress phases={phases} />
          {nonProcessSteps.length > 0 && (
            <div style={{ padding: '0 16px 12px' }}>
              <StepsTimeline steps={nonProcessSteps} />
            </div>
          )}
        </div>
      )}

      {/* 无 processPhases 时单独展示步骤 */}
      {!hasProcessPhases && nonProcessSteps.length > 0 && (
        <div className="response-card" style={{ padding: '10px 16px' }}>
          <StepsTimeline steps={nonProcessSteps} />
        </div>
      )}

      {/* 工具调用时间线 */}
      {toolResults.length > 0 && (
        <div className="response-card" style={{ padding: '12px 16px' }}>
          <div className="tool-timeline">
            {toolResults.map((tr, idx) => (
              <ToolResultCard
                key={tr.id}
                toolType={tr.toolType}
                toolName={tr.toolName}
                content={tr.content}
                status={tr.status}
                loading={tr.loading}
                isLast={idx === toolResults.length - 1}
              />
            ))}
          </div>
        </div>
      )}

      {/* Sub-Agent 卡片 */}
      {subAgents.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {subAgents.map((sa) => (
            <SubAgentCard key={sa.taskId} sa={sa} />
          ))}
        </div>
      )}

      {/* 动态组件 */}
      {widgets.map((widget) => (
        <div key={widget.id} className="response-card" style={{ overflow: 'visible' }}>
          {renderWidget(widget.component, widget.props, widget.id)}
        </div>
      ))}

      {/* 最终回答 */}
      {answer && (
        <div className="response-answer response-card">
          {renderAnswer(answer)}
          {isLive && !answerComplete && <span className="cursor-blink">▊</span>}
        </div>
      )}
    </div>
  )
}

export default ResponseBlock
