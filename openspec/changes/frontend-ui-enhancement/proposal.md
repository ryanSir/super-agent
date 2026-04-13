## Why

当前前端响应页面过于简陋：思考过程不可见、工具调用缺乏层次感、步骤流程无法直观感知，与 Perplexity、Claude.ai、Gemini 等主流产品的体验差距明显。需要对整体 UI 进行系统性重设计，让用户能清晰感知 Agent 的推理过程和执行状态。

## What Changes

- **响应详情页重设计**：参考 Perplexity/Claude.ai 设计语言，将响应区域重构为分层卡片式布局，包含思考过程、执行流程、工具输出、最终回答四个清晰区块
- **思考过程可视化**：思考内容以流式打字效果展示，配合动态脑波动画，可折叠/展开，完成后显示耗时
- **工具调用时间线**：每个工具调用以卡片形式展示，包含工具名、类型标签、参数预览、执行状态（loading/success/failed）、结果内容（可展开）
- **执行流程进度条**：顶部显示 planning → executing 阶段进度，配合步骤编号和状态图标
- **Skill 选择弹窗升级**：增加 skill 图标、分类标签、描述截断优化，选中态更明显，支持键盘导航高亮动画
- **子 Agent 状态卡片**：并行子 Agent 以独立卡片展示，包含名称、进度消息、token 用量、完成状态
- **响应区域整体视觉升级**：统一间距、字体层级、色彩系统，增加微动效（淡入、展开动画）

## Capabilities

### New Capabilities
- `response-detail-layout`: 响应详情页分层布局系统，包含思考/流程/工具/回答四区块的视觉层次和交互逻辑
- `tool-call-timeline`: 工具调用时间线组件，展示每个工具的调用参数、执行状态和结果内容
- `skill-picker-enhanced`: 升级版 Skill 选择弹窗，支持图标、分类、更好的键盘导航体验

### Modified Capabilities
- `a2ui-protocol`: 前端对 A2UI 事件的渲染映射需更新，以支持新的分层展示逻辑（非协议变更，仅渲染层调整）

## Impact

- **修改文件**：`frontend-deepagent/src/App.tsx`、`frontend-deepagent/src/components/ResponseBlock.tsx`、`frontend-deepagent/src/components/SkillMention.tsx`、`frontend-deepagent/src/components/ThinkingSection.tsx`、`frontend-deepagent/src/components/StepsTimeline.tsx`、`frontend-deepagent/src/components/ToolResultCard.tsx`、`frontend-deepagent/src/components/globals.css`
- **新增文件**：`frontend-deepagent/src/components/SubAgentCard.tsx`（替代现有 SubAgentStatus.tsx）、`frontend-deepagent/src/components/ProcessProgress.tsx`
- **无后端变更**：所有改动仅限前端渲染层，不涉及 API 协议或后端逻辑
- **无破坏性变更**：现有 A2UI 事件类型和 MessageHandler 状态结构保持不变

## Non-goals

- 不新增任何后端 API 或修改 A2UI 事件协议
- 不引入新的前端状态管理库（保持现有 React hooks 方案）
- 不实现响应历史的持久化存储
- 不做移动端适配（当前为桌面优先）
- 不修改 ComponentRegistry 中的动态组件（DataWidget、ArtifactPreview 等）