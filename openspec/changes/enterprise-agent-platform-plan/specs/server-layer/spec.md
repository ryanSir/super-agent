## ADDED Requirements

### Requirement: FastAPI + WebSocket 双通道服务
系统 SHALL 提供 REST API（FastAPI）和 WebSocket 双通道。REST API 用于请求/响应模式，WebSocket 用于双向实时通信（ask_clarification、实时编辑等）。

#### Scenario: REST API 查询
- **WHEN** 客户端 POST /api/agent/query
- **THEN** 系统 SHALL 返回 session_id，客户端通过 SSE 端点获取流式结果

#### Scenario: WebSocket 连接
- **WHEN** 客户端建立 WebSocket 连接到 /ws/{session_id}
- **THEN** 系统 SHALL 维持双向通道，支持客户端主动发送消息（如澄清回复）

#### Scenario: WebSocket 断线重连
- **WHEN** WebSocket 连接断开
- **THEN** 客户端重连后 SHALL 恢复会话状态，不丢失未读消息

### Requirement: SQLite Session Store
系统 SHALL 使用 SQLite 持久化会话状态，替换内存存储。会话数据包括：session_id、user_id、status、messages、metadata、created_at、updated_at。

#### Scenario: 会话创建
- **WHEN** 新请求到达
- **THEN** 系统 SHALL 在 SQLite 中创建会话记录，状态为 CREATED

#### Scenario: 会话恢复
- **WHEN** 服务重启后客户端请求恢复会话
- **THEN** 系统 SHALL 从 SQLite 加载会话状态，继续执行（如果会话未完成）

#### Scenario: 会话过期清理
- **WHEN** 会话超过 24 小时未活动
- **THEN** 系统 SHALL 标记为 EXPIRED，定期清理任务删除过期数据

### Requirement: JWT + API Key 认证
系统 SHALL 支持 JWT Token 和 API Key 两种认证方式。JWT 用于 Web 客户端，API Key 用于程序化调用。

#### Scenario: JWT 认证
- **WHEN** 请求携带有效 JWT Token
- **THEN** 系统 SHALL 解析 Token 获取 user_id 和权限，允许访问

#### Scenario: API Key 认证
- **WHEN** 请求携带 X-API-Key header
- **THEN** 系统 SHALL 验证 API Key 有效性，映射到对应用户

#### Scenario: 认证失败
- **WHEN** 请求未携带认证信息或认证无效
- **THEN** 系统 SHALL 返回 401 Unauthorized

### Requirement: 计费 Checkpoint
系统 SHALL 在每次 LLM 调用后记录 token 消耗（input_tokens / output_tokens / model / cost），支持 per-request 和 per-session 汇总。

#### Scenario: Token 记录
- **WHEN** 一次 LLM 调用完成
- **THEN** 系统 SHALL 记录 input_tokens、output_tokens、model_name、estimated_cost

#### Scenario: Session 汇总
- **WHEN** 会话结束
- **THEN** 系统 SHALL 汇总该会话所有 LLM 调用的 token 和成本

### Requirement: ACP Bridge Endpoint
系统 SHALL 提供 ACP Bridge 端点，支持跨通道（Web / IM / CLI）Session 接续。同一用户在不同通道的会话 SHALL 可以无缝切换。

#### Scenario: 跨通道接续
- **WHEN** 用户在 Web 端发起会话后切换到钉钉继续
- **THEN** 系统 SHALL 通过 ACP Bridge 恢复会话上下文，用户无需重复描述

#### Scenario: 多通道并发
- **WHEN** 用户同时在 Web 和 CLI 使用
- **THEN** 系统 SHALL 为每个通道维护独立会话，共享用户记忆
