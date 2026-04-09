/**
 * 工具结果卡片（可折叠）
 *
 * 支持 skill / mcp / native_worker / sandbox 四种类型。
 */

import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'

type ToolResultCardProps = {
  toolType: 'skill' | 'mcp' | 'native_worker' | 'sandbox'
  toolName: string
  content: string
  status: 'success' | 'failed'
  loading?: boolean
}

const TYPE_ICONS: Record<string, string> = {
  skill: '🛠️',
  mcp: '🌐',
  native_worker: '⚙️',
  sandbox: '🔒',
}

const NAME_ICONS: Record<string, string> = {
  'paper-search': '📄',
  'baidu-search': '🔍',
  'direct-baidu-search': '🔍',
  'exec-baidu-search': '🔍',
  'ai-ppt-generator': '📑',
  'google_ai_search': '🌐',
  'patsnap_search': '🔍',
  'patsnap_fetch': '📋',
  'rag_retrieval': '🗃️',
  'db_query': '🗄️',
  'api_call': '🔗',
}

function ToolResultCard({ toolType, toolName, content, status, loading }: ToolResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const icon = NAME_ICONS[toolName] || TYPE_ICONS[toolType] || '🛠️'

  if (loading) {
    return (
      <div className="tool-result-card tool-result-loading">
        <div className="tool-result-header">
          <span className="tool-result-icon">{icon}</span>
          <span className="tool-result-name">{toolName}</span>
          <span className="tool-result-badge badge-loading">执行中<span className="loading-dots">...</span></span>
        </div>
      </div>
    )
  }

  const preview = content.length > 120 ? content.slice(0, 120) + '...' : content

  return (
    <div className={`tool-result-card tool-result-${status}`}>
      <div className="tool-result-header" onClick={() => setExpanded(!expanded)}>
        <span className="tool-result-icon">{icon}</span>
        <span className="tool-result-name">{toolName}</span>
        <span className={`tool-result-badge badge-${status}`}>
          {status === 'success' ? '成功' : '失败'}
        </span>
        <span className="tool-result-toggle">{expanded ? '▲' : '▼'}</span>
      </div>
      {!expanded && (
        <div className="tool-result-preview">{preview}</div>
      )}
      {expanded && (
        <div className="tool-result-content">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}

export default ToolResultCard
