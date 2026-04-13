## ADDED Requirements

### Requirement: Skill 弹窗视觉升级
Skill 选择弹窗 SHALL 展示每个 skill 的图标（emoji）、名称和描述，选中项 SHALL 有明显的高亮背景和左侧彩色边框指示。弹窗 SHALL 有圆角卡片样式、阴影和模糊背景。

#### Scenario: 弹窗展示 skill 列表
- **WHEN** 用户输入 "/" 触发弹窗
- **THEN** 弹窗显示所有 skill，每项包含图标、名称（加粗）、描述（截断至 60 字符）

#### Scenario: 选中项高亮
- **WHEN** 键盘导航或鼠标悬停到某个 skill
- **THEN** 该项背景变为主题色半透明，左侧显示 3px 彩色边框，过渡动画 150ms

#### Scenario: 过滤后无结果
- **WHEN** 用户输入过滤词后无匹配 skill
- **THEN** 弹窗显示"没有匹配的 Skill"提示文字，不显示空列表

### Requirement: Skill 图标映射
弹窗 SHALL 根据 skill name 映射对应 emoji 图标，未匹配时显示默认图标 🔧。

#### Scenario: 已知 skill 图标
- **WHEN** skill.name 在图标映射表中存在（如 "patent-legal-status" → ⚖️）
- **THEN** 弹窗该 skill 项显示对应 emoji

#### Scenario: 未知 skill 图标兜底
- **WHEN** skill.name 不在图标映射表中
- **THEN** 显示默认图标 🔧

### Requirement: Skill 弹窗键盘导航动画
键盘导航切换选中项时 SHALL 有平滑滚动，确保选中项始终在弹窗可视区域内。

#### Scenario: 键盘向下导航超出可视区
- **WHEN** 用户按 ArrowDown 且选中项在弹窗底部以下
- **THEN** 弹窗内容平滑滚动，使选中项完整可见

#### Scenario: 键盘向上导航超出可视区
- **WHEN** 用户按 ArrowUp 且选中项在弹窗顶部以上
- **THEN** 弹窗内容平滑滚动，使选中项完整可见
