/**
 * 思考过程折叠区
 *
 * - 流式进行中：强制展开，显示打字光标
 * - 完成后：自动折叠，标题显示耗时
 * - 用户可手动切换展开/折叠
 */

import React, { useState, useEffect, useRef } from 'react'

type ThinkingSectionProps = {
  content: string
  isActive?: boolean
}

function ThinkingSection({ content, isActive = false }: ThinkingSectionProps) {
  const [expanded, setExpanded] = useState(false)
  const [elapsed, setElapsed] = useState<number | null>(null)
  const startTimeRef = useRef<number | null>(null)
  const wasActiveRef = useRef(false)

  // 记录开始时间
  useEffect(() => {
    if (isActive && startTimeRef.current === null) {
      startTimeRef.current = Date.now()
    }
  }, [isActive])

  // isActive 从 true → false 时计算耗时，自动折叠
  useEffect(() => {
    if (wasActiveRef.current && !isActive && startTimeRef.current !== null) {
      const secs = Math.round((Date.now() - startTimeRef.current) / 1000)
      setElapsed(secs)
      setExpanded(false)
    }
    wasActiveRef.current = isActive
  }, [isActive])

  // 流式进行中强制展开
  useEffect(() => {
    if (isActive) setExpanded(true)
  }, [isActive])

  if (!content && !isActive) return null

  const label = isActive
    ? '思考中...'
    : elapsed !== null
    ? `已思考 ${elapsed}s`
    : '思考过程'

  return (
    <div className="thinking-section response-card">
      <div className="thinking-header" onClick={() => setExpanded((e) => !e)}>
        <span className="thinking-icon">{isActive ? '💭' : '✨'}</span>
        <span className="thinking-label">{label}</span>
        <span className="thinking-toggle">{expanded ? '收起 ▲' : '展开 ▼'}</span>
      </div>
      <div className={`thinking-content${expanded ? ' expanded' : ''}`}>
        {content}
        {isActive && <span className="cursor-blink">▊</span>}
      </div>
    </div>
  )
}

export default ThinkingSection
