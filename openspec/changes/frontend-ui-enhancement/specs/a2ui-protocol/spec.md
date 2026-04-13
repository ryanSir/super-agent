## MODIFIED Requirements

### Requirement: 前端渲染 process_update 事件
前端 SHALL 将 process_update 事件渲染为独立的 ProcessProgress 组件，展示 planning 和 executing 两个阶段的状态，而非仅在 StepsTimeline 中作为普通步骤显示。ProcessProgress SHALL 固定显示在响应区块顶部，在任意 process_update 事件到达后出现。

#### Scenario: 收到 planning 阶段事件
- **WHEN** 收到 process_update(phase=planning, status=in_progress)
- **THEN** ProcessProgress 组件出现，planning 节点显示加载动画，executing 节点为灰色

#### Scenario: 收到 executing 阶段事件
- **WHEN** 收到 process_update(phase=executing, status=in_progress)
- **THEN** planning 节点变为完成状态（绿色对勾），executing 节点显示加载动画

#### Scenario: 所有阶段完成
- **WHEN** 收到 process_update(phase=executing, status=completed)
- **THEN** 两个节点均为完成状态，进度条完全填充

#### Scenario: process_update 事件不再创建 StepsTimeline 条目
- **WHEN** 收到任意 process_update 事件
- **THEN** StepsTimeline 中不新增对应步骤条目（由 ProcessProgress 专门处理）
