/**
 * Skill 快捷选择弹窗
 *
 * 在 textarea 中输入 / 时弹出，支持过滤、键盘导航、回车选中。
 * 升级：图标映射、两行布局、选中态左边框、scrollIntoView
 */

import React, { useRef, useEffect } from 'react'

export type Skill = {
  name: string
  description: string
}

type Props = {
  skills: Skill[]
  filter: string
  selectedIndex: number
  onSelect: (skill: Skill) => void
}

const SKILL_ICON_MAP: Record<string, string> = {
  'patent-legal-status': '⚖️',
  'paper-search': '📄',
  'baidu-search': '🔍',
  'google-search': '🔍',
  'ai-ppt-generator': '📑',
  'code-runner': '💻',
  'data-analysis': '📊',
  'web-scraper': '🕷️',
  'image-gen': '🎨',
  'translator': '🌐',
  'summarizer': '📝',
  'rag-retrieval': '🗃️',
  'db-query': '🗄️',
}

function getSkillIcon(name: string): string {
  return SKILL_ICON_MAP[name] ?? '🔧'
}

function SkillMention({ skills, filter, selectedIndex, onSelect }: Props) {
  const listRef = useRef<HTMLDivElement>(null)
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])

  const filtered = skills.filter(
    (s) =>
      filter === '' ||
      s.name.toLowerCase().includes(filter.toLowerCase()) ||
      s.description.toLowerCase().includes(filter.toLowerCase()),
  )

  // 选中项变化时滚动到可视区
  useEffect(() => {
    const el = itemRefs.current[selectedIndex]
    if (el) {
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedIndex])

  if (filtered.length === 0) {
    return (
      <div className="skill-mention-popup">
        <div className="skill-mention-header">Skills</div>
        <div style={{ padding: '12px', fontSize: 13, color: 'var(--text-secondary)', textAlign: 'center' }}>
          没有匹配的 Skill
        </div>
      </div>
    )
  }

  return (
    <div className="skill-mention-popup" ref={listRef}>
      <div className="skill-mention-header">Skills</div>
      {filtered.map((skill, idx) => (
        <div
          key={skill.name}
          ref={(el) => { itemRefs.current[idx] = el }}
          className={`skill-mention-item ${idx === selectedIndex ? 'selected' : ''}`}
          onMouseDown={(e) => {
            e.preventDefault()
            onSelect(skill)
          }}
        >
          <span className="skill-mention-icon">{getSkillIcon(skill.name)}</span>
          <div className="skill-mention-body">
            <span className="skill-mention-name">/{skill.name}</span>
            <span className="skill-mention-desc">
              {skill.description.length > 60 ? skill.description.slice(0, 60) + '...' : skill.description}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

export default SkillMention
