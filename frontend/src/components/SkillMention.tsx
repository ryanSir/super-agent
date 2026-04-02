/**
 * Skill 快捷选择弹窗
 *
 * 在 textarea 中输入 / 时弹出，支持过滤、键盘导航、回车选中。
 */

import React from 'react'

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

function SkillMention({ skills, filter, selectedIndex, onSelect }: Props) {
  const filtered = skills.filter(
    (s) =>
      filter === '' ||
      s.name.toLowerCase().includes(filter.toLowerCase()) ||
      s.description.toLowerCase().includes(filter.toLowerCase()),
  )

  if (filtered.length === 0) return null

  return (
    <div className="skill-mention-popup">
      <div className="skill-mention-header">Skills</div>
      {filtered.map((skill, idx) => (
        <div
          key={skill.name}
          className={`skill-mention-item ${idx === selectedIndex ? 'selected' : ''}`}
          onMouseDown={(e) => {
            e.preventDefault() // 防止 textarea 失焦
            onSelect(skill)
          }}
        >
          <span className="skill-mention-name">/{skill.name}</span>
          <span className="skill-mention-desc">{skill.description}</span>
        </div>
      ))}
    </div>
  )
}

export default SkillMention
