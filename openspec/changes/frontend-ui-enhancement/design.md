## Context

当前前端响应区域（`ResponseBlock.tsx`）采用线性堆叠布局：思考 → 步骤 → 工具结果 → 回答，各区块之间缺乏视觉层次，工具调用信息密度低，思考过程展示单调。对比 Perplexity（来源卡片 + 分步推理）、Claude.ai（思考折叠块 + 工具调用内联）、Gemini（步骤气泡 + 进度指示），差距主要在：信息层次感、动效反馈、工具输出可读性。

现有组件结构清晰，`MessageHandler.ts` 的 `ResponseState` 已包含所有必要数据（thinking、steps、toolResults、subAgents、widgets、answer），无需修改数据层，只需重构渲染层。

## Goals / Non-Goals

**Goals:**
- 响应详情页重构为分层卡片式布局，四个语义区块清晰分离
- 思考过程增加流式打字动效和折叠交互
- 工具调用以时间线形式展示，含参数预览和结果展开
- Skill 选择弹窗视觉升级，增加图标和分类
- 统一微动效系统（淡入、展开、状态切换）
- 保持现有 `ResponseState` 数据结构不变

**Non-Goals:**
- 不修改后端 API 或 A2UI 事件协议
- 不引入新的状态管理库
- 不做移动端适配
- 不修改 ComponentRegistry 中的动态组件

## Decisions

### 决策 1：CSS-only 动效 vs 动画库

**选择**：CSS transitions + keyframes，不引入 Framer Motion 或 GSAP。

**理由**：项目当前无动画库依赖，引入 Framer Motion 会增加 ~40KB bundle。现有需求（淡入、展开、脉冲）用 CSS 完全可实现，且性能更好（GPU 加速）。

**备选**：Framer Motion — 开发体验更好但包体积代价不值得。

### 决策 2：工具调用时间线布局

**选择**：左侧竖线 + 节点圆点的时间线样式，每个工具调用为独立卡片，可展开查看完整结果。

**理由**：与 `StepsTimeline` 现有设计语言一致，避免引入全新视觉模式。工具调用天然是有序序列，时间线是最直观的表达。

**备选**：网格卡片布局 — 适合并行工具，但当前场景以串行为主。

### 决策 3：思考区块展示策略

**选择**：默认折叠（完成后），流式时展开并显示打字动效；完成后标题显示耗时。

**理由**：与 Claude.ai 行为一致，用户关注最终答案，思考过程是辅助信息。流式时展开保证用户感知到 Agent 在工作。

### 决策 4：Skill 弹窗图标来源

**选择**：使用 emoji 作为 skill 图标（从 skill name 映射），不依赖图标库。

**理由**：skill 列表动态加载，无法预知所有 skill。emoji 映射表维护简单，无需额外资源。

### 决策 5：组件文件组织

**选择**：新增 `ProcessProgress.tsx`（阶段进度条），重构 `SubAgentStatus.tsx` 为 `SubAgentCard.tsx`，其余在原文件内升级。

**理由**：最小化新文件数量，降低维护成本。`SubAgentStatus` 改动较大（从列表项升级为独立卡片），值得新建文件。

## Risks / Trade-offs

- **动效性能**：大量 CSS animation 在低端设备可能卡顿 → 通过 `prefers-reduced-motion` media query 降级为无动效
- **工具结果截断**：后端 content 已截断至 500 字符，展开后仍可能信息不完整 → 在卡片底部注明"内容已截断"
- **Skill 图标映射维护**：新增 skill 时需手动更新映射表 → 提供默认图标兜底，映射表集中在一处
- **折叠状态管理**：多个可折叠区块的状态需要在组件内维护，不影响全局状态 → 各组件内部 useState 管理，不上提

## Migration Plan

纯前端改动，无数据迁移。直接替换组件文件，`npm run dev` 验证即可。无需 feature flag，无回滚风险。

## Open Questions

- Skill 弹窗是否需要展示 skill 的参数说明？（当前 API 只返回 name + description）→ 暂不实现，等后端扩展 skill metadata
