## 1. 样式系统基础

- [x] 1.1 在 `globals.css` 中新增动效 CSS 变量（`--anim-fade-in`、`--anim-slide-up`）和 `@keyframes fadeSlideIn`，并添加 `prefers-reduced-motion` 降级规则
- [x] 1.2 在 `globals.css` 中新增工具类型颜色 token（`--color-skill`、`--color-mcp`、`--color-worker`、`--color-sandbox`）及对应徽章样式 `.tool-badge-*`
- [x] 1.3 在 `globals.css` 中新增响应区块卡片基础样式 `.response-card`（背景、圆角、内边距、边框）

## 2. ProcessProgress 组件

- [x] 2.1 新建 `frontend-deepagent/src/components/ProcessProgress.tsx`，接收 `phases: {name: string, status: 'pending'|'running'|'completed'|'failed'}[]` props，渲染两节点水平进度条
- [x] 2.2 在 `globals.css` 中添加 `.process-progress`、`.process-node`、`.process-line` 样式，节点状态对应不同颜色和图标

## 3. ThinkingSection 升级

- [x] 3.1 在 `ThinkingSection.tsx` 中添加 `startTime` ref，在 `isActive` 从 true 变 false 时计算耗时秒数，标题显示"已思考 Xs"
- [x] 3.2 在 `ThinkingSection.tsx` 中实现折叠逻辑：`isActive=true` 时强制展开，`isActive` 变 false 时自动折叠，用户可手动切换
- [x] 3.3 在 `globals.css` 中为 `.thinking-content` 添加 `max-height` 过渡动画实现平滑展开/折叠

## 4. ToolCallTimeline 重构

- [x] 4.1 重构 `ToolResultCard.tsx`：将布局改为左侧时间线节点（状态图标）+ 右侧卡片，节点与卡片之间有竖线连接
- [x] 4.2 在 `ToolResultCard.tsx` 中实现展开/折叠逻辑：默认折叠显示前 120 字符预览，点击展开渲染完整 Markdown 内容
- [x] 4.3 在 `ToolResultCard.tsx` 中根据 `toolType` 渲染对应颜色徽章（skill/mcp/native_worker/sandbox）和节点图标
- [x] 4.4 在 `globals.css` 中添加 `.tool-timeline`、`.tool-timeline-node`、`.tool-timeline-line`、`.tool-card` 样式

## 5. SubAgentCard 重构

- [x] 5.1 新建 `frontend-deepagent/src/components/SubAgentCard.tsx`，接收 `SubAgentState` props，渲染独立卡片（名称、进度消息、状态徽章、token 用量、结果展开）
- [x] 5.2 在 `globals.css` 中添加 `.sub-agent-card`、`.sub-agent-header`、`.sub-agent-progress` 样式
- [x] 5.3 在 `ResponseBlock.tsx` 中将 `SubAgentStatus` 替换为 `SubAgentCard`，按 `subAgents` 数组渲染

## 6. SkillMention 升级

- [x] 6.1 在 `SkillMention.tsx` 中新增 `SKILL_ICON_MAP` 常量（skill name → emoji 映射），未匹配时返回 🔧
- [x] 6.2 在 `SkillMention.tsx` 中更新列表项布局：左侧图标 + 右侧名称/描述两行，描述截断至 60 字符
- [x] 6.3 在 `SkillMention.tsx` 中为选中项添加左侧彩色边框（`border-left: 3px solid var(--color-primary)`）
- [x] 6.4 在 `SkillMention.tsx` 中为列表容器添加 `ref`，在 `selectedIndex` 变化时调用 `scrollIntoView` 确保选中项可见
- [x] 6.5 在 `globals.css` 中更新 `.skill-mention-popup`、`.skill-mention-item` 样式（圆角卡片、阴影、选中态过渡）

## 7. ResponseBlock 重构

- [x] 7.1 在 `ResponseBlock.tsx` 中新增 `processPhases` 状态推导逻辑，从 `steps` 中提取 process_update 相关步骤转换为 `ProcessProgress` 所需 props
- [x] 7.2 在 `ResponseBlock.tsx` 中将四个区块（思考/流程/工具/回答）各自包裹在 `.response-card` 容器中，并添加 `fadeSlideIn` 动效类
- [x] 7.3 在 `ResponseBlock.tsx` 中将 `StepsTimeline` 与 `ProcessProgress` 组合：`ProcessProgress` 在上，`StepsTimeline` 在下（仅显示非 process_update 步骤）
- [x] 7.4 在 `globals.css` 中更新 `.response-block` 布局间距，确保各卡片之间有 12px 间隔

## 8. MessageHandler 调整

- [x] 8.1 在 `MessageHandler.ts` 的 `process_update` 事件处理分支中，移除向 `steps` 数组添加条目的逻辑，改为更新独立的 `processPhases` 字段
- [x] 8.2 在 `MessageHandler.ts` 的 `ResponseState` 类型中新增 `processPhases: {phase: string, status: string}[]` 字段，并在 `createInitialState` 中初始化为空数组
