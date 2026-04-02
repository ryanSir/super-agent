/**
 * 思考过程折叠区
 */

import React, { useState } from 'react'

type ThinkingSectionProps = {
  content: string
  isActive?: boolean
}

function ThinkingSection({ content, isActive = false }: ThinkingSectionProps) {
  const [expanded, setExpanded] = useState(false)

  if (!content && !isActive) return null

  return (
    <div className="thinking-section">
      <div className="thinking-header" onClick={() => setExpanded(!expanded)}>
        <span className="thinking-icon">{isActive ? '💭' : '✨'}</span>
        <span className="thinking-label">{isActive ? '思考中...' : '思考过程'}</span>
        <span className="thinking-toggle">{expanded ? '收起' : '展开'}</span>
      </div>
      {expanded && content && (
        <div className="thinking-content">{content}</div>
      )}
    </div>
  )
}

export default ThinkingSection
