## Context

原有 `SandboxManager` 只支持 E2B 远程沙箱，本地开发时依赖腾讯云环境，调试成本高。同时 pi agent 从旧版（`pi-mono --instruction`）升级到 v0.62+（`pi --print --mode json`），参数格式完全变化，IPC 解析逻辑需要同步更新。

当前状态：
- `SandboxManager` 硬编码 E2B SDK 调用，无法在本地运行
- `pi_agent_config.py` 使用旧版 `pi-mono` 参数，v0.62+ 不兼容
- `sandbox_worker.py` 使用轮询机制等待 `.pi_state.jsonl`，但 `pi --print` 是同步退出的，轮询无意义
- `ipc.py` 解析旧版自定义 JSONL 格式，与 pi v0.62+ 的标准事件格式不兼容

## Goals / Non-Goals

**Goals:**
- `SANDBOX_PROVIDER=local` 时，`SandboxManager` 使用本地临时目录 + subprocess 执行
- `SANDBOX_PROVIDER=tencent/e2b` 时，行为与原来完全一致
- pi agent 启动参数适配 v0.62+，provider/model 通过环境变量配置
- IPC 解析适配 pi v0.62+ 的 `agent_end` 事件格式

**Non-Goals:**
- 本地模式不提供安全隔离，不适用于生产
- 不修改 E2B 远程沙箱的任何行为
- 不支持本地模式的资源限制

## Decisions

### 决策 1：SandboxManager 内部双后端，对外接口不变

`SandboxManager` 保持相同的公共接口（`create_sandbox`、`execute_command`、`write_file`、`read_file`、`destroy_sandbox`），内部根据 `_is_local` 属性路由到 `_local_*` 或 `_e2b_*` 私有方法。

**理由**：`SandboxWorker` 无需感知 provider，切换环境只改 `.env`，不改代码。

**替代方案**：独立的 `LocalSandboxManager` 子类——但会导致 `SandboxWorker` 需要条件实例化，改动范围更大。

### 决策 2：新增 `get_work_dir(sandbox_id)` 方法

本地模式的工作目录是运行时动态创建的临时目录，E2B 模式是配置文件里的固定路径。`SandboxWorker` 通过 `get_work_dir()` 获取实际路径，用于构建启动脚本和执行命令。

**理由**：避免 `SandboxWorker` 直接读取 `settings.e2b.e2b_work_dir`，解耦 worker 和 provider 实现细节。

### 决策 3：移除轮询，改为同步等待

`pi --print` 执行完成后进程退出，输出已写入文件。原来的轮询机制（每 2 秒读一次 `.pi_state.jsonl`）在 `pi --print` 模式下没有意义——进程退出前文件可能还没写完，退出后才是完整输出。

**改为**：`execute_command()` 同步等待进程退出，然后一次性读取输出文件。

### 决策 4：`SANDBOX_PI_PROVIDER` / `SANDBOX_PI_MODEL` 环境变量

pi agent 的 LLM provider 和 model 因环境而异（本地用 `my-gateway/gpt-4o`，生产可能不同），通过环境变量配置，默认值 `my-gateway` / `gpt-4o`。

## Risks / Trade-offs

- **[风险] 本地模式无隔离**：pi agent 可以访问宿主机所有文件和命令。→ 缓解：文档明确标注"仅用于开发"，生产环境通过 `SANDBOX_PROVIDER` 强制使用 E2B。
- **[风险] 临时目录残留**：若进程异常退出，`destroy_sandbox` 未被调用，临时目录会残留在 `/tmp`。→ 缓解：`SandboxWorker.execute()` 的 `finally` 块保证调用 `destroy_sandbox`。
- **[Trade-off] 同步执行阻塞**：`pi --print` 可能运行数分钟，期间 asyncio 事件循环被 `subprocess` 阻塞。→ 缓解：使用 `asyncio.create_subprocess_shell` 异步执行，不阻塞事件循环。

## Migration Plan

1. 在 `.env` 中设置 `SANDBOX_PROVIDER=local` 启用本地模式
2. 确认本地已安装 `pi`（`npm install -g @mariozechner/pi-coding-agent`）
3. 在 `.env` 中配置 `SANDBOX_PI_PROVIDER` 和 `SANDBOX_PI_MODEL`
4. 切回生产：将 `SANDBOX_PROVIDER` 改回 `tencent`，无需其他改动

**回滚**：git revert，无状态变更。
