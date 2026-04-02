## Why

E2B 远程沙箱依赖腾讯云环境，本地开发时无法调试沙箱任务（`pi-mono` 未安装、网络不通、镜像缺依赖）。需要一种本地降级模式，让开发者在不依赖远程沙箱的情况下完整测试沙箱执行流程。

## Non-goals

- 不提供真正的安全隔离（本地模式仅用于开发/测试，生产必须使用 E2B）
- 不修改 E2B 远程沙箱的任何逻辑
- 不支持本地模式下的资源限制（CPU/内存/网络）

## What Changes

- 新增 `SANDBOX_PROVIDER=local` 支持：`SandboxManager` 根据 provider 自动路由到本地 subprocess 或远程 E2B
- 本地模式使用 `tempfile.mkdtemp()` 创建临时目录作为沙箱工作目录，执行完自动清理
- 新增 `SandboxManager.get_work_dir(sandbox_id)` 方法，返回实际工作目录（本地为临时目录，E2B 为配置路径）
- 适配 pi v0.62+ 启动参数：从 `pi-mono --instruction` 改为 `pi --print --mode json --provider --model`
- 新增 `SANDBOX_PI_PROVIDER` / `SANDBOX_PI_MODEL` 环境变量，控制 pi agent 使用的 LLM provider 和模型
- 新增 `ipc.py` 中的 `extract_final_answer()` 函数，直接从 pi JSONL 输出提取最终答案
- 重写 `parse_jsonl()`，适配 pi v0.62+ 的 `agent_end` / `message_start` 事件格式
- `SandboxWorker.execute()` 改为同步等待 pi 执行完成（移除轮询机制），执行完读取输出文件

## Capabilities

### New Capabilities

- `local-sandbox`: 本地 subprocess 沙箱执行模式，通过 `SANDBOX_PROVIDER=local` 启用，使用临时目录隔离工作区，支持完整的 pi agent 执行流程

### Modified Capabilities

- `workers`: SandboxWorker 执行流程变更——从"异步启动 + 轮询状态文件"改为"同步执行 + 读取输出"；pi agent 启动参数格式更新

## Impact

- `src/workers/sandbox/sandbox_manager.py` — 新增本地模式实现，重构为 E2B/local 双后端
- `src/workers/sandbox/pi_agent_config.py` — 启动脚本模板重写，新增 `SANDBOX_PI_PROVIDER`/`SANDBOX_PI_MODEL` 配置读取
- `src/workers/sandbox/ipc.py` — `parse_jsonl()` 重写，新增 `extract_final_answer()`
- `src/workers/sandbox/sandbox_worker.py` — 移除轮询逻辑，改为同步执行
- `src/config/settings.py` — `E2BSettings` 新增 `sandbox_pi_provider`、`sandbox_pi_model` 字段
- `.env` — 新增 `SANDBOX_PROVIDER`、`SANDBOX_PI_PROVIDER`、`SANDBOX_PI_MODEL` 配置项
