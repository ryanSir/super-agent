# 01. Plugin 概念定义

## 目标

Plugin 是 Agent 平台的标准化扩展机制，用于把外部系统、数据源、工具调用、技能流程或 UI 组件接入 Agent 平台。

本文件回答三个问题：

1. Plugin 是什么。
2. Plugin 不是什么。
3. Plugin 与 Skill、Tool、MCP、OpenAPI、App 的关系。

## 核心定义

中文定义：

> Plugin 是一个声明式、可安装、可授权、可运行、可观测、可分发的 Agent 能力包，用于将外部系统、数据源、工具调用、技能流程或 UI 组件接入 Agent 平台。

英文定义：

> Plugin is a declarative, installable, permissioned, executable, observable and distributable capability package that extends the Agent Platform with external systems, data sources, tool invocations, skills, workflows and optional UI components.

## 命名建议

对外可以继续使用 **Plugin**，因为它容易被开发者和客户理解。

内部架构模型建议使用 **Capability Package，能力包**，因为它更准确地表达了这个对象不是单个 API、单个工具或单个 UI，而是一组可治理的 Agent 能力集合。

建议命名关系：

| 场景 | 建议名称 |
| --- | --- |
| 产品界面、市场、开发者文档 | Plugin |
| 架构模型、manifest、内部设计 | Capability Package |
| 平台管理模块 | Plugin Manager |
| 开发工具 | Plugin SDK / Plugin CLI |
| 分发仓库 | Plugin Registry |
| 运行宿主 | Plugin Runtime Host |

## Plugin 不是什么

Plugin 不是单个 tool。Tool 是 Plugin 可以暴露的一种能力。

Plugin 不是 MCP server。MCP 是 Plugin 支持的一种协议或运行时接入方式。

Plugin 不是一个普通 API connector。API connector 是 Plugin 可以包含的一类能力。

Plugin 不是单纯的前端 app。App/UI 是 Plugin 可以提供的用户交互面。

Plugin 不是 prompt 模板。Skill 可以包含提示词、流程和约束，但 Plugin 是更大的分发和治理单元。

## 与核心概念的关系

```text
Plugin / Capability Package
   ├── Skill：告诉 Agent 如何完成某类任务
   ├── Tool：Agent 可调用的结构化函数
   ├── MCP Server：一种工具协议接入方式
   ├── OpenAPI Connector：一种企业 API 接入方式
   ├── Data Source：文档、数据库、SaaS、知识库等数据接入
   ├── Workflow：可复用流程或自动化编排
   ├── App/UI：配置页、操作面板、结果展示
   ├── Auth/Credentials：认证和凭据声明
   └── Policy：权限、审计、人审、数据边界
```

| 概念 | 定位 |
| --- | --- |
| Plugin | 能力包、安装包、治理单元 |
| Skill | Agent 行为指导和领域工作流说明 |
| Tool | 可被模型调用的结构化能力 |
| MCP | Tool/Data 的协议之一 |
| OpenAPI | 企业 API 接入协议之一 |
| App | 用户可见的配置和交互界面 |
| Connector | 面向外部系统的数据/操作接入器 |

关键结论：**MCP 不是 Plugin 本身，MCP 是 Plugin 支持的一种运行时或工具协议。**

## 设计原则

1. Plugin 是能力包，不是单个工具。
2. Plugin 是分发和治理单元，不是具体执行能力本身。
3. Plugin 必须声明能力、权限、认证和运行方式。
4. Agent Runtime 不直接理解插件内部实现，而是通过标准能力元数据使用插件。
5. 插件能力必须可安装、可授权、可观测、可升级、可下线。

