## ADDED Requirements

### Requirement: 多提供商模型管理
系统 SHALL 支持 Anthropic / OpenAI / Ollama / 国产模型（通义千问/文心一言）等多个 LLM 提供商，通过统一的 Provider 接口调用。提供商配置 SHALL 通过环境变量或配置文件管理。

#### Scenario: OpenAI 兼容调用
- **WHEN** 配置 EXECUTION_MODEL=gpt-4o
- **THEN** 系统 SHALL 通过 OpenAI API 调用 gpt-4o，返回统一格式的响应

#### Scenario: Ollama 本地模型
- **WHEN** 配置 EXECUTION_MODEL=ollama/llama3
- **THEN** 系统 SHALL 通过本地 Ollama 服务调用，不依赖外部网络

#### Scenario: 提供商不可用
- **WHEN** 配置的 LLM 提供商 API 返回 5xx 错误
- **THEN** 系统 SHALL 按降级链尝试备选提供商，所有提供商不可用时返回服务不可用错误

### Requirement: Streaming 流式输出
系统 SHALL 支持 LLM 响应的流式输出，token 级别实时推送到前端。流式过程中 SHALL 支持 token 计数和成本估算。

#### Scenario: 正常流式输出
- **WHEN** Agent 执行产生 LLM 响应
- **THEN** 每个 token SHALL 实时通过 SSE 推送到前端，延迟 < 100ms

#### Scenario: 流式中断恢复
- **WHEN** 流式输出过程中网络中断
- **THEN** 客户端重连后 SHALL 从断点继续接收，不丢失已生成内容

### Requirement: 自动降级 + 重试 + 熔断
系统 SHALL 实现 LLM 调用的三级容错：重试（同提供商重试 2 次）→ 降级（切换备选提供商）→ 熔断（连续失败 5 次后暂停该提供商 60 秒）。

#### Scenario: 单次失败重试
- **WHEN** LLM API 返回 429 (Rate Limit) 或 500 错误
- **THEN** 系统 SHALL 等待指数退避后重试，最多 2 次

#### Scenario: 降级切换
- **WHEN** 主提供商重试 2 次仍失败
- **THEN** 系统 SHALL 切换到降级链中的下一个提供商

#### Scenario: 熔断触发
- **WHEN** 某提供商连续 5 次调用失败
- **THEN** 系统 SHALL 熔断该提供商 60 秒，期间所有请求直接路由到备选提供商

### Requirement: 模型路由三档
系统 SHALL 支持三档模型路由：planning（规划用，高推理能力）、execution（执行用，平衡能力和成本）、fast（快速响应，低延迟低成本）。每档 SHALL 可独立配置模型。

#### Scenario: 规划阶段用 planning 模型
- **WHEN** ReasoningEngine 进行复杂度评估或任务分解
- **THEN** 系统 SHALL 使用 PLANNING_MODEL 配置的模型

#### Scenario: 执行阶段用 execution 模型
- **WHEN** Agent 执行主流程（工具调用+推理）
- **THEN** 系统 SHALL 使用 EXECUTION_MODEL 配置的模型

#### Scenario: 快速响应用 fast 模型
- **WHEN** 模糊区间 LLM 兜底分类或简单意图识别
- **THEN** 系统 SHALL 使用 FAST_MODEL 配置的模型，响应时间 < 2 秒
