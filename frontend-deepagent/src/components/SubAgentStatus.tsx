/**
 * Sub-Agent 执行状态展示组件
 *
 * 展示各 Sub-Agent 的执行进度和结果。
 */

import React from 'react'

type SubAgentState = {
  taskId: string
  agentName: string
  status: 'running' | 'completed' | 'failed'
  result?: string
  tokenUsage?: Record<string, number>
  error?: string
}

const AGENT_LABELS: Record<string, string> = {
  researcher: '🔍 Research Agent',
  analyst: '📊 Analysis Agent',
  writer: '✍️ Writing Agent',
}

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  running: {
    borderLeft: '3px solid #3b82f6',
    background: '#eff6ff',
  },
  completed: {
    borderLeft: '3px solid #22c55e',
    background: '#f0fdf4',
  },
  failed: {
    borderLeft: '3px solid #ef4444',
    background: '#fef2f2',
  },
}

export default function SubAgentStatus({
  subAgents,
}: {
  subAgents: SubAgentState[]
}) {
  if (!subAgents.length) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', margin: '8px 0' }}>
      {subAgents.map((sa) => (
        <div
          key={sa.taskId}
          style={{
            padding: '10px 14px',
            borderRadius: '6px',
            fontSize: '13px',
            ...STATUS_STYLES[sa.status],
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600 }}>
              {AGENT_LABELS[sa.agentName] || sa.agentName}
            </span>
            <span style={{ fontSize: '12px', opacity: 0.7 }}>
              {sa.status === 'running' && '执行中...'}
              {sa.status === 'completed' && '✓ 完成'}
              {sa.status === 'failed' && '✗ 失败'}
            </span>
          </div>

          {sa.status === 'completed' && sa.result && (
            <div style={{ marginTop: '6px', fontSize: '12px', opacity: 0.8, lineHeight: 1.5 }}>
              {sa.result.length > 200 ? sa.result.slice(0, 200) + '...' : sa.result}
            </div>
          )}

          {sa.status === 'failed' && sa.error && (
            <div style={{ marginTop: '6px', fontSize: '12px', color: '#dc2626' }}>
              {sa.error}
            </div>
          )}

          {sa.tokenUsage && (
            <div style={{ marginTop: '4px', fontSize: '11px', opacity: 0.5 }}>
              tokens: {Object.entries(sa.tokenUsage).map(([k, v]) => `${k}=${v}`).join(' ')}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
