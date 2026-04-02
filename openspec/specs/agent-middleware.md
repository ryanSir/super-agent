### Requirement: Middleware 基类定义
系统 SHALL 提供 `AgentMiddleware` 抽象基类，定义四个可覆写钩子：`before_agent`、`after_agent`、`on_tool_call`、`on_tool_error`。所有钩子 MUST 为 async 方法。基类 MUST 位于 `src/middleware/base.py`。

#### Scenario: 自定义 middleware 继承基类
- **WHEN** 开发者创建一个继承 `AgentMiddleware` 的子类并只覆写 `after_agent`
- **THEN** 其余钩子使用默认空实现，不影响请求处理流程

#### Scenario: 钩子方法签名校验
- **WHEN** middleware 子类的钩子方法不是 async
- **THEN** 在 pipeline 注册时 MUST 抛出 `TypeError`

### Requirement: MiddlewareContext 贯穿请求生命周期
系统 SHALL 提供 `MiddlewareContext` 数据类，包含 `session_id`、`trace_id`、`messages`（当前对话历史）、`token_usage`（累计 token 使用）、`metadata`（可扩展字典）。MiddlewareContext MUST 在 pipeline 入口创建，贯穿所有 middleware。

#### Scenario: 上下文在 middleware 间共享
- **WHEN** middleware A 在 `before_agent` 中向 `context.metadata` 写入 `{"loop_count": 0}`
- **THEN** middleware B 在 `after_agent` 中可以读取到 `context.metadata["loop_count"]`

#### Scenario: token_usage 累计更新
- **WHEN** Agent 执行完成后 token_usage 被更新
- **THEN** 后续 middleware 的 `after_agent` 钩子可以读取到最新的 token 使用量

### Requirement: MiddlewarePipeline 按序执行
系统 SHALL 提供 `MiddlewarePipeline` 类，接受有序的 middleware 列表。`before_agent` 钩子 MUST 按列表顺序执行，`after_agent` 钩子 MUST 按列表逆序执行（洋葱模型）。Pipeline MUST 位于 `src/middleware/pipeline.py`。

#### Scenario: 正常执行顺序
- **WHEN** pipeline 包含 [MW_A, MW_B, MW_C] 三个 middleware
- **THEN** 执行顺序为 A.before → B.before → C.before → agent → C.after → B.after → A.after

#### Scenario: before_agent 抛出异常
- **WHEN** MW_B 的 `before_agent` 抛出异常
- **THEN** pipeline MUST 停止执行后续 middleware，直接抛出异常，不执行 agent

#### Scenario: after_agent 抛出异常
- **WHEN** MW_C 的 `after_agent` 抛出异常
- **THEN** pipeline MUST 停止逆序执行，将异常传播给调用方

### Requirement: Pipeline 配置化开关
系统 SHALL 通过 `MiddlewareSettings.enabled` 配置项控制 pipeline 是否启用。当 `enabled=false` 时，MUST 直接调用 agent 函数，跳过所有 middleware。

#### Scenario: 关闭 middleware
- **WHEN** 配置 `middleware.enabled=false`
- **THEN** `run_orchestrator()` 直接执行，不经过任何 middleware 包装

#### Scenario: 默认启用
- **WHEN** 未配置 `middleware.enabled`
- **THEN** 默认值为 `true`，middleware pipeline 正常执行

### Requirement: TokenUsageMiddleware 记录 token 用量
系统 SHALL 提供 `TokenUsageMiddleware`，在 `after_agent` 钩子中记录本次请求的 input_tokens、output_tokens、total_tokens 到结构化日志。MUST 使用现有的 Langfuse tracer 记录 token 指标。

#### Scenario: 正常记录
- **WHEN** Agent 执行完成，返回包含 token usage 信息的结果
- **THEN** middleware 将 token 用量写入结构化日志，格式为 `[session_id] LLM token usage: input=X output=Y total=Z`

#### Scenario: token usage 信息缺失
- **WHEN** Agent 返回结果中不包含 token usage 信息
- **THEN** middleware MUST 跳过记录，不抛出异常

### Requirement: LoopDetectionMiddleware 检测重复 tool 调用
系统 SHALL 提供 `LoopDetectionMiddleware`，使用滑动窗口追踪最近 N 次 tool call 的 hash（name + args）。当同一 hash 出现次数 >= `warn_threshold`（默认 3）时，注入警告消息。当出现次数 >= `hard_limit`（默认 5）时，强制终止 tool 调用。

#### Scenario: 触发警告
- **WHEN** Agent 连续 3 次调用相同 tool（相同 name 和 args）
- **THEN** middleware 向对话历史注入警告消息："[LOOP DETECTED] You are repeating the same tool calls. Stop calling tools and produce your final answer now."

#### Scenario: 触发强制终止
- **WHEN** Agent 连续 5 次调用相同 tool
- **THEN** middleware MUST 清除当前 tool_calls，强制 Agent 生成最终文本回答

#### Scenario: 不同参数不触发
- **WHEN** Agent 调用同一 tool 但参数不同
- **THEN** hash 不同，不触发循环检测

#### Scenario: 滑动窗口淘汰
- **WHEN** 滑动窗口大小为 20，第 21 次 tool call 进入
- **THEN** 最早的一次记录被淘汰

### Requirement: ToolErrorHandlingMiddleware 捕获 tool 异常
系统 SHALL 提供 `ToolErrorHandlingMiddleware`，在 `on_tool_error` 钩子中捕获 tool 执行异常，将其转换为错误消息返回给 Agent，而非让整个请求失败。错误消息 MUST 包含 tool 名称和异常摘要（截断至 500 字符）。

#### Scenario: tool 执行超时
- **WHEN** 某个 Worker tool 执行超时抛出 `asyncio.TimeoutError`
- **THEN** middleware 返回错误消息 "Error: Tool 'xxx' failed with TimeoutError: ..."，Agent 继续执行

#### Scenario: tool 执行抛出未知异常
- **WHEN** tool 执行抛出 `RuntimeError("unexpected")`
- **THEN** middleware 返回错误消息，Agent 可以选择重试或使用其他 tool

#### Scenario: 错误消息过长截断
- **WHEN** 异常消息超过 500 字符
- **THEN** 截断至 497 字符并追加 "..."

### Requirement: MemoryMiddleware 异步更新记忆
系统 SHALL 提供 `MemoryMiddleware`，在 `after_agent` 钩子中将对话内容（仅用户输入和最终 Agent 回复，过滤 tool 中间消息）异步提交到记忆更新队列。MUST 不阻塞主请求流程。

#### Scenario: 正常更新
- **WHEN** Agent 执行完成，对话包含用户输入和 Agent 回复
- **THEN** middleware 将过滤后的对话提交到记忆更新队列，主请求立即返回

#### Scenario: 无有效对话
- **WHEN** 对话中只有 tool 消息，没有用户输入或 Agent 回复
- **THEN** middleware MUST 跳过记忆更新

#### Scenario: 记忆系统未启用
- **WHEN** 配置 `memory.enabled=false`
- **THEN** middleware MUST 跳过所有记忆操作

### Requirement: SummarizationMiddleware 压缩长对话
系统 SHALL 提供 `SummarizationMiddleware`，在 `before_agent` 钩子中检查对话历史 token 数。当超过阈值（默认为 context window 的 70%）时，使用 `fast` 模型将早期对话压缩为摘要，替换原始消息。

#### Scenario: 触发摘要压缩
- **WHEN** 对话历史 token 数超过阈值
- **THEN** middleware 将最早的 N 条消息压缩为一条摘要消息，保留最近的消息不变

#### Scenario: 未超过阈值
- **WHEN** 对话历史 token 数未超过阈值
- **THEN** middleware 不做任何操作，对话历史保持不变

#### Scenario: 压缩失败降级
- **WHEN** LLM 摘要调用失败
- **THEN** middleware MUST 记录错误日志，保持原始对话历史不变，不阻塞请求
