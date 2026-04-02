## 1. 配置层

- [x] 1.1 在 `src/config/settings.py` 的 `E2BSettings` 中新增 `sandbox_pi_provider`（别名 `SANDBOX_PI_PROVIDER`，默认 `my-gateway`）和 `sandbox_pi_model`（别名 `SANDBOX_PI_MODEL`，默认 `gpt-4o`）字段

## 2. SandboxManager 双后端重构

- [x] 2.1 在 `src/workers/sandbox/sandbox_manager.py` 中新增 `_is_local` 属性，根据 `sandbox_provider == "local"` 判断
- [x] 2.2 新增 `get_work_dir(sandbox_id)` 方法，本地模式返回临时目录路径，E2B 模式返回 `settings.e2b_work_dir`
- [x] 2.3 实现 `_local_create(task)`：用 `tempfile.mkdtemp()` 创建临时目录，注入上下文文件和环境变量，存储 sandbox_id → 目录映射
- [x] 2.4 实现 `_local_exec(sandbox_id, command, timeout, cwd)`：用 `asyncio.create_subprocess_shell` 在临时目录执行命令
- [x] 2.5 将原有 E2B 逻辑提取为 `_e2b_create()` 和 `_e2b_exec()` 私有方法
- [x] 2.6 更新 `write_file`、`read_file`、`destroy_sandbox`、`destroy_all` 支持本地/E2B 双路由
- [x] 2.7 `_e2b_exec` 中的 `sandbox.commands.run()` 加上 `user="root"` 参数（修复腾讯云沙箱认证问题）

## 3. Pi Agent 启动参数适配

- [x] 3.1 重写 `src/workers/sandbox/pi_agent_config.py` 启动脚本模板，从 `pi-mono --instruction` 改为 `pi --print --mode json --provider {provider} --model {model}`
- [x] 3.2 `build_startup_command()` 从 `get_settings().e2b` 读取 `sandbox_pi_provider` 和 `sandbox_pi_model`
- [x] 3.3 更新 `build_env_vars()` 默认模型为 `gpt-4o`，移除旧版 `PI_OUTPUT_MODE`/`PI_SILENT_CONSOLE` 环境变量

## 4. IPC 解析适配 pi v0.62+

- [x] 4.1 重写 `src/workers/sandbox/ipc.py` 的 `parse_jsonl()`，解析 `agent_end`、`message_start`、`tool_result` 事件类型
- [x] 4.2 新增 `extract_final_answer(raw)` 函数，从 `agent_end.messages` 中提取最后一条 assistant 文本
- [x] 4.3 新增 `_extract_text(content)` 辅助函数，从 content 块列表中提取纯文本

## 5. SandboxWorker 执行流程重构

- [x] 5.1 移除 `_poll_state()` 轮询方法和 `POLL_INTERVAL` 常量
- [x] 5.2 `execute()` 改为同步等待 `execute_command()` 完成，进程退出后读取输出文件
- [x] 5.3 本地模式下直接使用 `settings.llm.openai_api_key` 作为 pi agent API Key，跳过 JWT 签发
- [x] 5.4 使用 `get_work_dir(sandbox_id)` 替换硬编码的 `settings.e2b.e2b_work_dir`
- [x] 5.5 更新 import，加入 `extract_final_answer`

## 6. 验证

- [x] 6.1 运行 `pytest tests/test_connectivity.py::TestSandboxConnectivity -v -s`，确认 4 个测试全部通过
- [x] 6.2 直接调用 `SandboxWorker.execute()` 验证 pi agent 能正确返回 `final_answer`
