## ADDED Requirements

### Requirement: 本地沙箱模式
系统 SHALL 在 `SANDBOX_PROVIDER=local` 时，使用本地临时目录和 subprocess 执行沙箱任务，无需 E2B SDK 或远程连接。

#### Scenario: 本地沙箱创建
- **WHEN** `SANDBOX_PROVIDER=local` 且调用 `create_sandbox(task)`
- **THEN** 系统 SHALL 在 `/tmp` 下创建唯一临时目录，返回格式为 `local-<hex12>` 的 sandbox_id

#### Scenario: 本地沙箱执行命令
- **WHEN** 调用 `execute_command(sandbox_id, command)` 且 sandbox_id 以 `local-` 开头
- **THEN** 系统 SHALL 使用 `asyncio.create_subprocess_shell` 在临时目录中执行命令，返回 `{stdout, stderr, exit_code}`

#### Scenario: 本地沙箱销毁
- **WHEN** 调用 `destroy_sandbox(sandbox_id)` 且为本地模式
- **THEN** 系统 SHALL 删除对应临时目录，不留残留文件

#### Scenario: 并发本地沙箱隔离
- **WHEN** 同时创建两个本地沙箱
- **THEN** 每个沙箱 SHALL 有独立的临时目录，互不干扰

#### Scenario: 本地沙箱异常清理
- **WHEN** 沙箱任务执行过程中抛出异常
- **THEN** `finally` 块 SHALL 确保 `destroy_sandbox` 被调用，临时目录被清理

### Requirement: Pi Agent 启动参数配置
系统 SHALL 通过 `SANDBOX_PI_PROVIDER` 和 `SANDBOX_PI_MODEL` 环境变量控制 pi agent 使用的 LLM provider 和模型，默认值分别为 `my-gateway` 和 `gpt-4o`。

#### Scenario: 使用默认配置启动
- **WHEN** `.env` 中未设置 `SANDBOX_PI_PROVIDER` 和 `SANDBOX_PI_MODEL`
- **THEN** 启动脚本 SHALL 使用 `--provider my-gateway --model gpt-4o`

#### Scenario: 使用自定义配置启动
- **WHEN** `.env` 中设置 `SANDBOX_PI_PROVIDER=openai` 和 `SANDBOX_PI_MODEL=gpt-4o-mini`
- **THEN** 启动脚本 SHALL 使用 `--provider openai --model gpt-4o-mini`

### Requirement: Pi v0.62+ JSONL 输出解析
系统 SHALL 解析 pi v0.62+ 的 `--mode json` 输出格式，从 `agent_end` 事件中提取最终答案。

#### Scenario: 正常提取最终答案
- **WHEN** pi 输出包含 `{"type":"agent_end","messages":[...]}` 且最后一条 assistant 消息有文本内容
- **THEN** `extract_final_answer()` SHALL 返回该文本内容

#### Scenario: 输出为空或解析失败
- **WHEN** pi 输出为空或不包含有效的 `agent_end` 事件
- **THEN** `extract_final_answer()` SHALL 返回空字符串，不抛出异常

#### Scenario: 工具调用事件解析
- **WHEN** pi 输出包含 `message_start` 事件且 content 中有 `tool_use` 块
- **THEN** `parse_jsonl()` SHALL 生成对应的 `ACTION` 阶段 `IPCMessage`
