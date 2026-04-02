## ADDED Requirements

### Requirement: Orchestrator 支持 token 级流式输出
Orchestrator 的最终回答生成 SHALL 使用 LLM 的流式 API，每个 token 产生后立即通过 `publish_event` 推送 `text_stream` 事件，不得等待完整响应后再推送。

#### Scenario: 正常流式输出
- **WHEN** Orchestrator 完成工具调用阶段，开始生成最终回答
- **THEN** 系统 SHALL 在收到第一个 LLM token 后 500ms 内推送第一个 `text_stream` 事件

#### Scenario: 流式中断处理
- **WHEN** LLM 流在输出过程中发生网络错误或超时
- **THEN** 系统 SHALL 推送 `session_failed` 事件，并在事件中包含已生成的部分文本长度

#### Scenario: 流式完成后历史存储
- **WHEN** LLM 流正常结束（所有 token 输出完毕）
- **THEN** 系统 SHALL 将所有 token 拼接为完整字符串存入会话历史 `_session_histories`

### Requirement: 移除人为分块延迟
系统 SHALL NOT 在 `text_stream` 事件推送之间引入任何人为的 `asyncio.sleep` 延迟。

#### Scenario: 无人为延迟
- **WHEN** 系统推送连续的 `text_stream` 事件
- **THEN** 相邻两个事件之间的间隔 SHALL 仅由 LLM 原生输出速度决定，不得超过 LLM token 间隔 + 50ms 系统开销

#### Scenario: 并发会话不互相阻塞
- **WHEN** 两个不同 session_id 的会话同时进行流式输出
- **THEN** 每个会话的 token 推送 SHALL 独立进行，互不阻塞
