/**
 * 工具调用时间线卡片
 *
 * 左侧：状态节点 + 竖线连接
 * 右侧：工具卡片（可展开查看完整结果）
 */

import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type ToolResultCardProps = {
  toolType: 'skill' | 'mcp' | 'native_worker' | 'sandbox'
  toolName: string
  content: string
  status: 'success' | 'failed'
  loading?: boolean
  isLast?: boolean
}

const TOOL_TYPE_CONFIG = {
  skill:         { label: 'Skill',   icon: '🛠️', badgeClass: 'tool-badge-skill' },
  mcp:           { label: 'MCP',     icon: '🌐', badgeClass: 'tool-badge-mcp' },
  native_worker: { label: 'Worker',  icon: '⚙️', badgeClass: 'tool-badge-worker' },
  sandbox:       { label: 'Sandbox', icon: '🔒', badgeClass: 'tool-badge-sandbox' },
}

function NodeIcon({ loading, status }: { loading?: boolean; status: 'success' | 'failed' }) {
  if (loading) {
    return (
      <span
        style={{
          display: 'block',
          width: 10,
          height: 10,
          borderRadius: '50%',
          border: '2px solid rgba(59,130,246,0.25)',
          borderTopColor: '#3b82f6',
          animation: 'spin 0.7s linear infinite',
        }}
      />
    )
  }
  if (status === 'success') {
    return (
      <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
        <path d="M3 7l2.5 2.5 5.5-5.5" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }
  return (
    <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
      <path d="M3 3l6 6M9 3l-6 6" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function ToolResultCard({ toolType, toolName, content, status, loading, isLast }: ToolResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const config = TOOL_TYPE_CONFIG[toolType] || TOOL_TYPE_CONFIG.mcp
  const nodeClass = loading ? 'node-loading' : status === 'success' ? 'node-success' : 'node-failed'
  const preview = content.length > 120 ? content.slice(0, 120) + '...' : content

  return (
    <div className="tool-timeline-item">
      {/* 左侧时间线 */}
      <div className="tool-timeline-left">
        <div className={`tool-timeline-node ${nodeClass}`}>
          <NodeIcon loading={loading} status={status} />
        </div>
        {!isLast && <div className="tool-timeline-line" />}
      </div>

      {/* 右侧卡片 */}
      <div className={`tool-card${status === 'failed' ? ' tool-card-failed' : ''}`}>
        <div
          className="tool-card-header"
          onClick={() => !loading && content && setExpanded((e) => !e)}
        >
          <span style={{ fontSize: 14 }}>{config.icon}</span>
          <span className="tool-card-name">{toolName}</span>
          <span className={`tool-type-badge ${config.badgeClass}`}>{config.label}</span>
          {!loading && (
            <span className={`tool-status-badge ${status === 'success' ? 'badge-success' : 'badge-failed'}`}>
              {status === 'success' ? '成功' : '失败'}
            </span>
          )}
          {!loading && content && (
            <span className={`tool-card-chevron${expanded ? ' expanded' : ''}`}>▼</span>
          )}
        </div>

        {loading && (
          <div className="tool-card-preview">
            <div className="tool-loading-dots">
              <span /><span /><span />
            </div>
          </div>
        )}

        {!loading && !expanded && content && (
          <div className="tool-card-preview">{preview}</div>
        )}

        {!loading && !content && (
          <div className="tool-card-preview" style={{ fontStyle: 'italic', opacity: 0.6 }}>（无输出）</div>
        )}

        {expanded && (
          <div className="tool-card-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

export default ToolResultCard
