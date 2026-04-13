## ADDED Requirements

### Requirement: 响应区域分层卡片布局
响应详情页 SHALL 将 Agent 回答拆分为四个语义区块，按顺序展示：思考过程（ThinkingSection）、执行流程（ProcessProgress + StepsTimeline）、工具调用（ToolCallTimeline）、最终回答（answer）。各区块之间 SHALL 有明确的视觉分隔，整体采用卡片容器包裹。

#### Scenario: 完整响应渲染
- **WHEN** ResponseState 包含 thinking、steps、toolResults 和 answer 全部字段
- **THEN** 页面从上到下依次渲染四个区块，每个区块有独立卡片背景和内边距

#### Scenario: 仅有最终回答
- **WHEN** ResponseState 只有 answer 字段，thinking/steps/toolResults 均为空
- **THEN** 只渲染回答区块，不显示空的思考/步骤/工具区块

#### Scenario: 流式响应中间状态
- **WHEN** isLive=true 且 answer 尚未开始流式输出
- **THEN** 显示思考区块（若有 thinking）或步骤区块（若有 steps），不显示空的回答区块

### Requirement: 思考过程折叠交互
思考区块 SHALL 支持折叠/展开交互。流式进行中（isActive=true）时 SHALL 默认展开并显示打字动效光标；完成后 SHALL 默认折叠，标题显示"已思考 Xs"耗时信息。

#### Scenario: 流式思考展开状态
- **WHEN** isActive=true 且 thinking 内容非空
- **THEN** 思考区块展开，内容末尾显示闪烁光标，标题显示"思考中..."

#### Scenario: 思考完成折叠
- **WHEN** isActive 从 true 变为 false（思考完成）
- **THEN** 思考区块自动折叠，标题更新为"已思考 Xs"（X 为实际耗时秒数）

#### Scenario: 手动展开折叠
- **WHEN** 用户点击思考区块标题
- **THEN** 切换展开/折叠状态，内容区域以平滑动画展开或收起

### Requirement: 执行阶段进度指示
响应区域顶部 SHALL 显示 planning → executing 两阶段进度，每个阶段有状态图标（进行中/完成/失败）和标签文字。

#### Scenario: Planning 阶段进行中
- **WHEN** 收到 process_update(phase=planning, status=in_progress)
- **THEN** planning 节点显示旋转加载图标，executing 节点显示灰色待机状态

#### Scenario: 两阶段均完成
- **WHEN** 收到 process_update(phase=executing, status=completed)
- **THEN** 两个节点均显示绿色对勾图标，进度条填满

#### Scenario: 阶段失败
- **WHEN** 收到 process_update(status=failed)
- **THEN** 对应节点显示红色错误图标，后续节点保持灰色

### Requirement: 子 Agent 状态卡片
每个子 Agent SHALL 以独立卡片形式展示，包含：Agent 名称、当前进度消息、token 用量（完成后）、成功/失败状态徽章。

#### Scenario: 子 Agent 运行中
- **WHEN** 收到 sub_agent_started 事件
- **THEN** 显示新卡片，含 Agent 名称和"运行中"状态，进度消息区域为空

#### Scenario: 子 Agent 进度更新
- **WHEN** 收到 sub_agent_progress 事件
- **THEN** 对应卡片的进度消息更新为最新 progress 文本

#### Scenario: 子 Agent 完成
- **WHEN** 收到 sub_agent_completed(success=true) 事件
- **THEN** 卡片状态变为"完成"（绿色），显示 token 用量，结果内容可展开查看

#### Scenario: 子 Agent 失败
- **WHEN** 收到 sub_agent_completed(success=false) 事件
- **THEN** 卡片状态变为"失败"（红色），显示错误信息

### Requirement: 响应区块淡入动效
每个区块首次出现时 SHALL 有淡入 + 向上位移的入场动效（duration: 200ms, easing: ease-out）。

#### Scenario: 区块首次渲染
- **WHEN** 任意响应区块从无到有出现
- **THEN** 区块以 opacity 0→1、translateY 8px→0 的动效进入

#### Scenario: 减少动效偏好
- **WHEN** 系统设置 prefers-reduced-motion: reduce
- **THEN** 所有动效禁用，区块直接显示无过渡