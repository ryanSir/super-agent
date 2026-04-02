## Context

当前 `ChatMessage.tsx` 使用 emoji 字符作为头像（👤/🤖），消息布局为单列居中，用户消息和 AI 消息在视觉上没有明显区分。`globals.css` 中 `.chat-message` 为 flex 行布局但无左右对齐区分。整体风格与主流 AI 产品（Claude.ai、ChatGPT）差距明显。

## Goals / Non-Goals

**Goals:**
- 用户消息右对齐气泡，AI 消息左对齐卡片，形成清晰的对话层次
- 使用两张精美 SVG 头像图片替换 emoji，提升品质感
- 输入框升级为 textarea，支持多行输入，Enter 发送，Shift+Enter 换行
- Header 添加亮色/暗色主题切换按钮，偏好持久化到 localStorage
- 保持现有 ResponseBlock / StepsTimeline / ToolResultCard 组件不变

**Non-Goals:**
- 不修改后端通信逻辑
- 不引入 UI 组件库
- 不做移动端适配

## Decisions

### 1. 头像方案：内联 SVG Data URI

**选择**：将头像以 SVG Data URI 形式内联在 TypeScript 常量中，不新增图片文件。

**理由**：
- 无需配置 Vite 静态资源路径，零依赖
- SVG 可精确控制渐变、圆角、图形细节，视觉效果优于 PNG
- 两张头像体积极小（< 2KB），内联无性能损耗

**备选**：放在 `frontend/public/` 目录 → 需要处理 base path，部署时路径可能变化，放弃。

### 2. 布局方案：CSS Flexbox 左右对齐

**选择**：`.message-row` 使用 `display: flex`，用户消息 `justify-content: flex-end`，AI 消息 `justify-content: flex-start`。气泡最大宽度 72%。

**理由**：与 ChatGPT / Claude.ai 一致的主流模式，实现简单，无需引入新依赖。

**备选**：Grid 布局 → 对动态内容宽度控制不如 flexbox 直观，放弃。

### 3. 输入框：textarea 替换 input

**选择**：将 `<input type="text">` 替换为 `<textarea>`，通过 `onKeyDown` 处理 Enter/Shift+Enter。

**理由**：支持多行输入是 AI 对话产品的标配，用户体验显著提升。

### 4. AI 消息布局：头像 + 内容并排，不用气泡

**选择**：AI 回复不使用气泡，而是头像在左、内容区域在右的宽松卡片布局，与用户气泡形成视觉对比。

**理由**：AI 回复通常包含 StepsTimeline、ToolResultCard 等复杂组件，气泡宽度限制会破坏这些组件的展示效果。

### 5. 主题切换：CSS 变量 + data-theme 属性

**选择**：在 `<html>` 元素上设置 `data-theme="light"` 属性，CSS 中用 `[data-theme="light"]` 选择器覆盖 `:root` 变量。React 侧用 `useState` + `useEffect` 管理，偏好写入 localStorage。

**理由**：
- 无需引入 Context 或状态管理库，实现最简
- CSS 变量覆盖方案切换瞬时完成，无闪烁
- `data-theme` 挂在 `<html>` 上，所有子元素自动继承，无需传 props

**备选**：动态切换 CSS class → 与现有 `:root` 变量冲突处理更复杂，放弃。

## Risks / Trade-offs

- [textarea 高度自适应] 需要用 JS 动态调整 `rows` 或用 `field-sizing: content`（CSS 新特性，兼容性有限）→ 用 `onInput` 重置并设置 `scrollHeight` 实现自适应
- [SVG 内联维护成本] 头像修改需要改代码 → 可接受，头像不会频繁变更
- [AI 消息无气泡] 视觉上与用户消息对比度依赖颜色区分 → 通过背景色和左侧 border-left accent 线强化区分
