/**
 * 执行阶段进度条
 *
 * 展示 planning → executing 两阶段状态
 */

import React from 'react'

export type PhaseStatus = 'pending' | 'running' | 'completed' | 'failed'

export type Phase = {
  name: string
  label: string
  status: PhaseStatus
}

type Props = {
  phases: Phase[]
}

function NodeIcon({ status }: { status: PhaseStatus }) {
  if (status === 'running') {
    return (
      <span
        style={{
          display: 'block',
          width: 12,
          height: 12,
          borderRadius: '50%',
          border: '2px solid rgba(99,102,241,0.25)',
          borderTopColor: '#6366f1',
          animation: 'spin 0.7s linear infinite',
        }}
      />
    )
  }
  if (status === 'completed') {
    return (
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M3 7l2.5 2.5 5.5-5.5" stroke="#22c55e" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }
  if (status === 'failed') {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M3 3l6 6M9 3l-6 6" stroke="#ef4444" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  // pending
  return <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--border)', display: 'block' }} />
}

function ProcessProgress({ phases }: Props) {
  if (phases.length === 0) return null

  return (
    <div className="process-progress">
      {phases.map((phase, idx) => (
        <React.Fragment key={phase.name}>
          <div className={`process-node status-${phase.status}`}>
            <div className="process-node-icon">
              <NodeIcon status={phase.status} />
            </div>
            <span className="process-node-label">{phase.label}</span>
          </div>
          {idx < phases.length - 1 && (
            <div
              className={`process-line${phases[idx + 1].status !== 'pending' || phase.status === 'completed' ? ' filled' : ''}`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  )
}

export default ProcessProgress
