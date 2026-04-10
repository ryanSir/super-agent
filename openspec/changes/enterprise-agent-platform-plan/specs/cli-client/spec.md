## ADDED Requirements

### Requirement: Textual TUI 交互界面
系统 SHALL 提供基于 Textual 的终端交互界面，支持对话输入、流式输出渲染、工具调用状态展示。

#### Scenario: 交互模式
- **WHEN** 用户运行 `python cli.py`
- **THEN** 系统 SHALL 启动 TUI 界面，显示输入框和对话历史区域

#### Scenario: 流式输出
- **WHEN** Agent 产生流式响应
- **THEN** TUI SHALL 实时渲染 Markdown 格式输出，支持代码块语法高亮

#### Scenario: 工具调用展示
- **WHEN** Agent 调用工具
- **THEN** TUI SHALL 显示工具名称和状态（执行中/完成/失败），不显示完整参数

### Requirement: in-process 模式
系统 SHALL 支持 in-process 嵌入式调用，Python 代码可直接导入并调用 Agent，无需启动 HTTP 服务。

#### Scenario: 嵌入式调用
- **WHEN** Python 代码执行 `from src_deepagent import create_agent; result = await agent.run("query")`
- **THEN** 系统 SHALL 在当前进程内执行 Agent，返回结果对象

#### Scenario: 无服务依赖
- **WHEN** in-process 模式运行
- **THEN** 系统 SHALL 不依赖 Redis/HTTP Server，使用内存替代

### Requirement: --json 结构化输出
系统 SHALL 支持 --json 标志，输出结构化 JSON 结果，便于脚本集成和管道处理。

#### Scenario: JSON 输出
- **WHEN** 用户运行 `python cli.py --json "1+1等于几"`
- **THEN** 系统 SHALL 输出 JSON 格式：{"answer": "...", "tokens": {...}, "duration_ms": ...}

#### Scenario: 管道集成
- **WHEN** CLI 输出通过管道传递给 jq
- **THEN** 输出 SHALL 是合法的单行 JSON，可被 jq 正确解析

### Requirement: 会话管理
系统 SHALL 支持 CLI 会话管理：resume（恢复历史会话）、history（查看会话列表）、delete（删除会话）。

#### Scenario: 恢复会话
- **WHEN** 用户运行 `python cli.py --resume <session_id>`
- **THEN** 系统 SHALL 加载历史会话上下文，继续对话

#### Scenario: 查看历史
- **WHEN** 用户运行 `python cli.py --history`
- **THEN** 系统 SHALL 列出最近 20 个会话，包含 session_id、时间、首条消息摘要
