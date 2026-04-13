/**
 * Sub-Agent 独立卡片
 *
 * 展示单个 Sub-Agent 的名称、进度、状态、token 用量和结果
 */

import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { SubAgentState } from '../engine/MessageHandler'

const AGENT_LABELS: Record<string, string> = {
  researcher: '🔍 Research Agent',
  analyst: '📊 Analysis Agent',
  writer: '✍️ Writing Agent',
}

function SubAgentCard({ sa }: { sa: SubAgentState }) {
  const [expanded, setExpanded] = useState(false)
  const label = AGENT_LABELS[sa.agentName] || `🤖 ${sa.agentName}`
  const statusClass = `sub-agent-status-badge sub-agent-status-${sa.status}`
  const statusLabel = sa.status === 'running' ? '执行中' : sa.status === 'completed' ? '完成' : '失败'

  return (
    <div className="sub-agent-card">
      <div
        className="sub-agent-header"
        onClick={() => (sa.result || sa.error) && setExpanded((e) => !e)}
      >
        <span className="sub-agent-icon">🤖</span>
        <span className="sub-agent-name">{label}</span>
        <span className={statusClass}>{statusLabel}</span>
        {(sa.result || sa.error) && (
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{expanded ? '▲' : '▼'}</span>
        )}
      </div>

      {sa.status === 'running' && sa.result && (
        <div className="sub-agent-progress">{sa.result}</div>
      )}

      {sa.tokenUsage && (
        <div className="sub-agent-tokens">
          tokens: {Object.entries(sa.tokenUsage).map(([k, v]) => `${k}=${v}`).join(' · ')}
        </div>
      )}

      {expanded && sa.status === 'completed' && sa.result && (
        <div className="sub-agent-result">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{sa.result}</ReactMarkdown>
        </div>
      )}

      {expanded && sa.status === 'failed' && sa.error && (
        <div className="sub-agent-result" style={{ color: 'var(--error)' }}>{sa.error}</div>
      )}
    </div>
  )
}

export default SubAgentCard
