## MODIFIED Requirements

### Requirement: A2UI 组件类型扩展
A2UI 协议 SHALL 扩展支持更多组件类型：form（表单输入）、carousel（轮播卡片）、timeline（时间线）、diff（代码对比）、terminal（终端输出）、map（地图展示）。每个新组件 SHALL 在 ComponentRegistry 中注册。

#### Scenario: Form 组件
- **WHEN** Agent 输出 {"type": "form", "fields": [...]}
- **THEN** 前端 SHALL 渲染表单，用户填写后通过 WebSocket 回传数据

#### Scenario: Diff 组件
- **WHEN** Agent 输出代码修改建议
- **THEN** 前端 SHALL 使用 diff 组件展示修改前后对比，支持逐行审查

#### Scenario: 未知组件降级
- **WHEN** 收到未注册的组件类型
- **THEN** 前端 SHALL 显示 JSON 原始数据作为 fallback

### Requirement: A2UI 交互事件回传
A2UI 组件 SHALL 支持交互事件回传，用户在组件上的操作（点击/输入/选择）SHALL 通过 WebSocket 发送到 Agent，Agent 可基于交互结果继续执行。

#### Scenario: 按钮点击回传
- **WHEN** 用户点击 A2UI 组件中的 "确认" 按钮
- **THEN** 前端 SHALL 发送 {"event": "click", "component_id": "...", "action": "confirm"} 到 Agent

#### Scenario: 表单提交回传
- **WHEN** 用户填写 form 组件并提交
- **THEN** 前端 SHALL 发送表单数据到 Agent，Agent 基于数据继续执行

### Requirement: ComponentRegistry 注册机制
新增 A2UI 组件 SHALL 通过 ComponentRegistry.register() 注册，注册信息包括：组件类型名、React 组件引用、JSON Schema（用于验证 Agent 输出）。

#### Scenario: 组件注册
- **WHEN** 开发者注册新组件 ComponentRegistry.register("timeline", TimelineComponent, schema)
- **THEN** A2UI 引擎 SHALL 能识别并渲染 timeline 类型的输出

#### Scenario: Schema 验证
- **WHEN** Agent 输出的 JSON 不符合组件 Schema
- **THEN** 前端 SHALL 显示验证错误提示，不渲染异常数据
