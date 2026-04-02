/**
 * 终端样式输出组件
 *
 * 展示沙箱内的命令执行日志，终端风格。
 */

import React, { useRef, useEffect } from 'react'

type TerminalViewProps = {
  lines: string[]
  title?: string
}

function TerminalView({ lines = [], title = 'Terminal' }: TerminalViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [lines])

  return (
    <div className="terminal-view">
      <div className="terminal-header">
        <span className="terminal-dot red" />
        <span className="terminal-dot yellow" />
        <span className="terminal-dot green" />
        <span className="terminal-title">{title}</span>
      </div>
      <div className="terminal-body" ref={containerRef}>
        {lines.map((line, i) => (
          <div key={i} className="terminal-line">
            <span className="terminal-prompt">$</span> {line}
          </div>
        ))}
      </div>
    </div>
  )
}

export default TerminalView
