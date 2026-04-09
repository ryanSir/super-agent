/**
 * 安全制品预览舱
 *
 * 使用 Sandboxed IFrame 渲染 Agent 生成的 HTML/代码制品。
 * 复刻 Claude Artifacts 的体验。
 */

import React, { useState } from 'react'

type ArtifactPreviewProps = {
  artifact_url?: string
  artifact_html?: string
  artifact_type?: 'html' | 'image' | 'code'
  title?: string
  // 兼容后端 emit_widget 传入的多种格式
  code?: string
  content?: string
  language?: string
}

function ArtifactPreview({
  artifact_url,
  artifact_html,
  artifact_type,
  title,
  code,
  content,
  language,
}: ArtifactPreviewProps) {
  // 兼容 {code, language} 和 {content, language} 格式
  const resolvedType = artifact_type || (code || content || language ? 'code' : 'html')
  const resolvedHtml = artifact_html || code || content || ''
  const [copied, setCopied] = useState(false)

  if (resolvedType === 'image' && artifact_url) {
    return (
      <div className="artifact-preview">
        {title && <div className="artifact-title">{title}</div>}
        <img src={artifact_url} alt={title || 'Artifact'} className="artifact-image" />
      </div>
    )
  }

  if (resolvedType === 'code') {
    const codeContent = resolvedHtml
    const handleCopy = () => {
      navigator.clipboard.writeText(codeContent).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
    }
    return (
      <div className="artifact-preview">
        {title && <div className="artifact-title">{title}</div>}
        <div className="code-block-wrap">
          <pre className="artifact-code"><code>{codeContent}</code></pre>
          <button className={`code-copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopy}>
            {copied ? '已复制' : '复制'}
          </button>
        </div>
      </div>
    )
  }

  // HTML 制品：使用 sandboxed iframe
  const htmlContent = resolvedHtml
  const srcDoc = artifact_url ? undefined : htmlContent

  return (
    <div className="artifact-preview">
      {title && <div className="artifact-title">{title}</div>}
      <iframe
        src={artifact_url}
        srcDoc={srcDoc}
        sandbox="allow-scripts"
        className="artifact-iframe"
        title={title || 'Artifact Preview'}
      />
    </div>
  )
}

export default ArtifactPreview
