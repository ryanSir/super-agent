## MODIFIED Requirements

### Requirement: text_stream 事件格式
`text_stream` 事件的 `delta` 字段 SHALL 包含 LLM 原生输出的 token 增量文本，不得对 token 进行固定字符数的重新分块。`is_final` 字段 SHALL 在最后一个 token 推送时设为 `true`。

#### Scenario: 正常 token 推送
- **WHEN** LLM 输出一个或多个 token
- **THEN** 系统 SHALL 推送 `{"event_type": "text_stream", "delta": "<token_text>", "is_final": false}`

#### Scenario: 最终 token 标记
- **WHEN** LLM 流结束，最后一个 token 被推送
- **THEN** 系统 SHALL 推送 `{"event_type": "text_stream", "delta": "<last_token>", "is_final": true}`

#### Scenario: 空 delta 过滤
- **WHEN** LLM 输出空字符串 token（如某些模型的空白 token）
- **THEN** 系统 SHALL NOT 推送 delta 为空字符串的 `text_stream` 事件
