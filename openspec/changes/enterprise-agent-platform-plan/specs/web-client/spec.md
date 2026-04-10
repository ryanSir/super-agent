## ADDED Requirements

### Requirement: 对话界面 + Streaming 渲染
系统 SHALL 提供 React 对话界面，支持用户输入和 Agent 响应的实时流式渲染。Markdown 内容 SHALL 实时解析渲染，代码块 SHALL 支持语法高亮。

#### Scenario: 流式渲染
- **WHEN** Agent 通过 SSE 推送 token
- **THEN** 前端 SHALL 实时追加渲染，用户可看到逐字输出效果

#### Scenario: Markdown 渲染
- **WHEN** Agent 输出包含 Markdown 格式（标题/列表/代码块/表格）
- **THEN** 前端 SHALL 正确渲染为富文本，代码块带语法高亮和复制按钮

#### Scenario: 长对话滚动
- **WHEN** 对话内容超过一屏
- **THEN** 前端 SHALL 自动滚动到最新消息，用户手动滚动时暂停自动滚动

### Requirement: Artifact 展示
系统 SHALL 支持多种 Artifact 类型的展示：代码（可编辑+运行）、图表（ECharts 渲染）、文件（下载链接）、表格（可排序+筛选）、终端输出（xterm 渲染）。

#### Scenario: 代码 Artifact
- **WHEN** Agent 输出代码块并标记为 artifact
- **THEN** 前端 SHALL 在独立面板展示代码，支持编辑、复制、一键运行

#### Scenario: 图表 Artifact
- **WHEN** Agent 调用 emit_chart 输出 ECharts 配置
- **THEN** 前端 SHALL 使用 ECharts 渲染交互式图表

#### Scenario: 终端 Artifact
- **WHEN** 沙箱执行产生终端输出
- **THEN** 前端 SHALL 使用 xterm.js 渲染终端样式输出，支持 ANSI 颜色

### Requirement: A2UI Server-Driven UI 渲染引擎
系统 SHALL 实现 A2UI 渲染引擎，Agent 输出 JSON 渲染指令，前端动态组装 UI 组件。新组件 SHALL 在 ComponentRegistry 中注册。

#### Scenario: 组件渲染
- **WHEN** Agent 输出 {"type": "chart", "config": {...}}
- **THEN** 前端 SHALL 从 ComponentRegistry 查找 chart 组件并渲染

#### Scenario: 未注册组件
- **WHEN** Agent 输出未注册的组件类型
- **THEN** 前端 SHALL 显示 fallback 提示 "不支持的组件类型: xxx"

#### Scenario: 交互事件回传
- **WHEN** 用户点击 A2UI 组件中的按钮
- **THEN** 前端 SHALL 将交互事件通过 WebSocket 回传给 Agent

### Requirement: Agent Hub 管理界面
系统 SHALL 提供 Agent Hub 界面，支持：Agent 列表展示、配置面板（模型选择/工具权限/System Prompt 编辑）、运行状态监控。

#### Scenario: Agent 列表
- **WHEN** 用户访问 Agent Hub 页面
- **THEN** 前端 SHALL 展示所有可用 Agent（预置+自定义），包含名称、描述、状态

#### Scenario: Agent 配置
- **WHEN** 用户编辑某个 Agent 的配置
- **THEN** 前端 SHALL 提供表单编辑模型选择、工具权限、System Prompt，保存后实时生效

#### Scenario: 运行监控
- **WHEN** 有 Agent 正在执行任务
- **THEN** Agent Hub SHALL 实时显示执行状态、token 消耗、工具调用链

### Requirement: Skill 渲染组件
系统 SHALL 为 Skill 执行结果提供专用渲染组件，根据 Skill 类型（搜索结果/数据表格/文件产物）选择最佳展示方式。

#### Scenario: 搜索结果渲染
- **WHEN** Skill 返回搜索结果列表
- **THEN** 前端 SHALL 渲染为卡片列表，包含标题、摘要、来源链接

#### Scenario: 文件产物渲染
- **WHEN** Skill 生成文件产物（图片/PDF）
- **THEN** 前端 SHALL 内联预览（图片直接显示，PDF 用 viewer），并提供下载按钮
