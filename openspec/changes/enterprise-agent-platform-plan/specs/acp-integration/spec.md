## ADDED Requirements

### Requirement: ACP 五能力对接
系统 SHALL 实现 ACP 协议的 5 个核心能力：messaging（消息收发）、notification（通知推送）、session（会话管理）、cron（定时任务）、webhook（事件回调）。

#### Scenario: messaging 能力
- **WHEN** IM 通道收到用户消息
- **THEN** 系统 SHALL 通过 ACP messaging 接口接收消息，路由到 Agent 处理

#### Scenario: notification 能力
- **WHEN** Agent 执行完成需要通知用户
- **THEN** 系统 SHALL 通过 ACP notification 接口推送通知到用户所在通道

#### Scenario: session 能力
- **WHEN** 用户在 IM 中发起新对话
- **THEN** 系统 SHALL 通过 ACP session 接口创建会话，关联用户身份

#### Scenario: cron 能力
- **WHEN** 用户设置定时任务 "每天 9 点发送日报"
- **THEN** 系统 SHALL 通过 ACP cron 接口注册定时触发器

#### Scenario: webhook 能力
- **WHEN** 外部系统触发 webhook 事件
- **THEN** 系统 SHALL 通过 ACP webhook 接口接收并路由到对应 Agent

### Requirement: OpenClaw 双向通信
系统 SHALL 与 OpenClaw 平台建立双向通信通道，支持从 OpenClaw 接收指令和向 OpenClaw 上报状态。

#### Scenario: 接收指令
- **WHEN** OpenClaw 下发 Agent 执行指令
- **THEN** 系统 SHALL 解析指令并创建对应的 Agent 执行任务

#### Scenario: 状态上报
- **WHEN** Agent 执行状态变更（开始/进行中/完成/失败）
- **THEN** 系统 SHALL 实时上报状态到 OpenClaw

### Requirement: IM 通道集成
系统 SHALL 支持钉钉 / 飞书 / 企业微信三个 IM 平台的集成，通过 ACP 协议统一接入。

#### Scenario: 钉钉集成
- **WHEN** 用户在钉钉群 @Agent
- **THEN** 系统 SHALL 接收消息，执行 Agent，将结果回复到钉钉群

#### Scenario: 飞书集成
- **WHEN** 用户在飞书中发送私聊消息给 Agent
- **THEN** 系统 SHALL 接收消息，执行 Agent，将结果回复到飞书私聊

#### Scenario: 富文本适配
- **WHEN** Agent 输出包含 Markdown 格式
- **THEN** 系统 SHALL 根据目标 IM 平台的能力适配格式（钉钉 Markdown / 飞书富文本 / 企微 Markdown）
