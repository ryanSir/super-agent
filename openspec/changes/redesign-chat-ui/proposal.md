## Why

当前聊天界面用户消息和 AI 回复都在同一列居中展示，头像使用 emoji 字符（👤/🤖），视觉层次混乱、辨识度低，与主流 AI 产品（ChatGPT、Claude.ai）的对话体验差距明显。需要重新设计为左右分栏的对话气泡布局，并使用精美的自定义头像图片提升品质感。

## What Changes

- **用户消息**：右对齐气泡布局，头像显示在右侧，使用自定义用户头像图片
- **AI 消息**：左对齐布局，头像显示在左侧，使用自定义 AI 头像图片
- **头像**：替换 emoji 为两张精美 SVG/PNG 头像图片（用户头像 + AI 头像）
- **气泡样式**：用户消息使用蓝色气泡，AI 消息使用深色卡片，增加圆角和阴影
- **输入框**：升级为多行 textarea，支持 Shift+Enter 换行，Enter 发送，底部居中展示
- **整体布局**：参考 Claude.ai / ChatGPT 风格，消息区域宽度适中，左右留白
- **主题切换**：Header 右上角添加切换按钮，支持亮色（白天）和暗色（夜晚）两套主题

## Non-goals

- 不修改后端 SSE/WebSocket 通信逻辑
- 不修改 ResponseBlock、StepsTimeline、ToolResultCard 等 AI 输出组件的内部逻辑
- 不引入新的 UI 组件库（保持纯 CSS + React）
- 不做移动端响应式适配

## Capabilities

### New Capabilities

- `chat-bubble-layout`: 左右分栏对话气泡布局，用户消息右对齐、AI 消息左对齐
- `custom-avatars`: 自定义头像图片资源（用户 + AI），替换 emoji 字符
- `theme-toggle`: 亮色/暗色主题切换，偏好持久化到 localStorage

### Modified Capabilities

- `chat-ui`: 现有聊天界面的视觉样式和布局结构变更

## Impact

- `frontend/src/components/ChatMessage.tsx`：重构布局结构，引入头像图片
- `frontend/src/styles/globals.css`：重写消息行、气泡、头像相关样式
- `frontend/src/App.tsx`：调整输入框为 textarea，更新 footer 布局
- `frontend/public/` 或 `frontend/src/assets/`：新增两张头像图片资源
- `frontend/src/App.tsx`：添加主题状态管理，Header 新增切换按钮
- `frontend/src/styles/globals.css`：新增亮色主题 CSS 变量覆盖