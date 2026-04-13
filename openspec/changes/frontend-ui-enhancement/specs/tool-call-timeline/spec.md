## ADDED Requirements

### Requirement: 工具调用时间线展示
工具调用区域 SHALL 以垂直时间线形式展示所有工具调用，左侧为连接线和状态节点，右侧为工具卡片。每个卡片 SHALL 包含：工具名称、工具类型标签（skill/mcp/native_worker/sandbox）、执行状态（loading/success/failed）。

#### Scenario: 工具调用进行中
- **WHEN** 收到 tool_call 事件，对应 toolResult.loading=true
- **THEN** 时间线节点显示旋转加载动画，卡片标题显示工具名，内容区显示"执行中..."

#### Scenario: 工具调用成功完成
- **WHEN** 收到 tool_result(status=success) 事件
- **THEN** 节点变为绿色对勾，卡片显示结果内容预览（前 120 字符），状态徽章为"成功"

#### Scenario: 工具调用失败
- **WHEN** 收到 tool_result(status=failed) 事件
- **THEN** 节点变为红色叉号，状态徽章为"失败"，内容显示错误信息

#### Scenario: 多工具串行调用
- **WHEN** 存在多个 toolResult 条目
- **THEN** 按 id 顺序从上到下排列，时间线连接线贯穿所有节点

### Requirement: 工具结果可展开查看
每个工具卡片 SHALL 支持点击展开/折叠完整结果内容，折叠时显示内容预览（前 120 字符），展开时以 Markdown 渲染完整内容。

#### Scenario: 折叠状态预览
- **WHEN** 工具卡片处于折叠状态（默认）
- **THEN** 显示内容前 120 字符，末尾显示"..."，右侧有展开箭头图标

#### Scenario: 展开查看完整内容
- **WHEN** 用户点击工具卡片
- **THEN** 卡片展开，以 Markdown 渲染完整 content，箭头图标旋转 180°

#### Scenario: 内容为空时
- **WHEN** tool_result.content 为空字符串
- **THEN** 折叠状态显示"（无输出）"，不显示展开箭头

### Requirement: 工具类型视觉区分
不同工具类型 SHALL 有不同的颜色标签和图标，以便用户快速识别工具来源。

#### Scenario: skill 类型工具
- **WHEN** toolType 为 "skill"
- **THEN** 类型标签显示蓝色"Skill"，节点图标为 🛠️

#### Scenario: mcp 类型工具
- **WHEN** toolType 为 "mcp"
- **THEN** 类型标签显示紫色"MCP"，节点图标为 🌐

#### Scenario: native_worker 类型工具
- **WHEN** toolType 为 "native_worker"
- **THEN** 类型标签显示绿色"Worker"，节点图标为 ⚙️

#### Scenario: sandbox 类型工具
- **WHEN** toolType 为 "sandbox"
- **THEN** 类型标签显示橙色"Sandbox"，节点图标为 🔒
