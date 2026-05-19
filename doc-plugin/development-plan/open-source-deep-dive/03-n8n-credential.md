# 03. n8n Credential 深度分析

## 结论先行

n8n 适合作为 credential schema、连接测试、connector 配置体验的设计参考。Credential 的生产实现大概率仍需自研或接入公司密钥系统。

## 适用模块

- Credential schema。
- 凭据配置表单。
- 连接测试。
- Connector UX。

## 需要重点分析的问题

- credential type 如何定义字段、必填项、secret 字段和展示脱敏。
- OAuth2、API Key、Basic Auth 等认证方式如何建模。
- 连接测试如何绑定 credential 和 connector。
- credential 与 workflow / node / connector 的引用关系。
- 凭据权限、共享、轮换和失效如何处理。

## 可复用点

- credential schema 设计。
- 连接测试产品体验。
- connector 配置表单设计。
- secret 字段脱敏和引用模型。

## 不适合直接复用的点

- n8n 面向 workflow automation，不完全等价于 Agent Plugin 平台。
- 生产凭据存储必须接公司密钥系统，不能直接沿用外部项目存储模型。
- 权限体系要接 workspace / agent / user，不应照搬 n8n 的工作流作用域。

## 建议动作

- 作为第一批 P0 深度分析。
- 输出 Credential schema 字段建议。
- 输出连接测试 API 和配置页字段建议。

