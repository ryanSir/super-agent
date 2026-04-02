## MODIFIED Requirements

### Requirement: SandboxWorker 执行流程
SandboxWorker SHALL 使用同步等待模式执行 pi agent：启动脚本写入沙箱后，调用 `execute_command()` 同步等待进程退出，进程退出后一次性读取输出文件提取最终答案。不得使用轮询机制等待状态文件。

#### Scenario: 正常执行完成
- **WHEN** pi agent 成功执行任务并退出
- **THEN** SandboxWorker SHALL 从输出文件中提取 `final_answer`，`success=True`

#### Scenario: pi agent 执行失败
- **WHEN** pi agent 进程以非零 exit_code 退出
- **THEN** SandboxWorker SHALL 尝试从输出文件提取部分答案；若无答案则 `success=False`，`error` 包含 stderr 信息

#### Scenario: 执行超时
- **WHEN** pi agent 执行时间超过 `task.timeout`
- **THEN** SandboxWorker SHALL 抛出 `SandboxTimeoutError`，并在 `finally` 块中销毁沙箱

#### Scenario: 本地模式使用真实 API Key
- **WHEN** `SANDBOX_PROVIDER=local`
- **THEN** SandboxWorker SHALL 直接使用 `settings.llm.openai_api_key` 作为 pi agent 的 API Key，不签发临时 JWT token
