## ADDED Requirements

### Requirement: 生成全局技术架构图
系统 SHALL 调用 fireworks-tech-graph skill，生成一张覆盖 Super Agent 所有技术组件的全局架构图，输出 SVG 和 PNG 两种格式，存放于 `doc-arch/` 目录。

#### Scenario: 成功生成架构图
- **WHEN** 执行 fireworks-tech-graph skill，传入完整的组件定义和 Claude 官方风格参数
- **THEN** 在 `doc-arch/` 目录下生成 `tech-arch-diagram.svg` 和 `tech-arch-diagram.png` 两个文件

#### Scenario: 输出文件已存在时覆盖
- **WHEN** `doc-arch/tech-arch-diagram.svg` 或 `.png` 已存在
- **THEN** skill 覆盖旧文件，生成最新版本，不报错退出

### Requirement: 架构图覆盖所有技术组件
架构图 SHALL 包含以下所有组件及其连接关系，不得遗漏：
- 用户层：Browser / API Client
- 前端层：React 18 + Vite、SSEClient、MessageHandler、ComponentRegistry、ECharts、xterm
- 网关层：FastAPI REST API、WebSocket Gateway
- 编排层：ReasoningEngine、AgentFactory、PydanticAI Agent、Sub-Agents（researcher/analyst/writer）
- Worker 层：Native Workers（RAG/DB/API/WebSearch）、Sandbox Worker（E2B/Local + Pi Agent）
- 工具/技能层：CapabilityRegistry、10 内置工具、Skills 插件、MCP 延迟加载
- 上下文层：Context Builder（12段 System Prompt）、Memory（Redis Profile+Facts）
- 流式层：Redis Stream、SSE 断点续传
- 存储层：Redis（会话/记忆/流）、Milvus（向量检索）
- 外部 AI 服务：Anthropic Claude API、LiteLLM（OpenAI 兼容）
- 沙箱：E2B Cloud、Local Sandbox
- 可观测性：Langfuse、结构化日志

#### Scenario: 组件完整性验证
- **WHEN** 架构图生成完成
- **THEN** 图中可识别的组件节点数量 SHALL 不少于 20 个，且上述各层均有对应节点

#### Scenario: 连接关系完整性
- **WHEN** 架构图生成完成
- **THEN** 前端→网关、网关→编排、编排→Worker、Worker→存储、编排→外部AI服务的主要数据流箭头均须存在

### Requirement: 采用 Claude 官方视觉风格
架构图 SHALL 使用 Claude 官方品牌风格：深色背景、品牌配色（橙色 #d97706、蓝色 #3b82f6）、清晰无衬线字体、分层泳道布局。

#### Scenario: 风格参数正确传入
- **WHEN** 调用 fireworks-tech-graph 时
- **THEN** 风格参数中 SHALL 包含 Claude 官方配色方案和深色背景设置

#### Scenario: 图片可读性
- **WHEN** 以 1920px 宽度查看生成的 PNG
- **THEN** 所有组件名称和连接标签均清晰可读，无文字重叠
