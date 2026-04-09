## MODIFIED Requirements

### Requirement: Worker 桥接暴露

Worker 层 SHALL 通过桥接工具（bridge.py）暴露给 deepagents Agent 和 Sub-Agent。WorkerProtocol 接口不变，桥接工具内部构建 TaskNode 并调用 Worker.execute()。

桥接工具持有 Worker 实例引用（进程内），主 Agent 和所有 Sub-Agent 共享同一批 Worker 实例。

#### Scenario: 多 Sub-Agent 共享 Worker
- **WHEN** 三个 Research Sub-Agent 并行调用 execute_rag_search
- **THEN** 三次调用共享同一个 RAGWorker 实例，Worker 内部通过 async 处理并发

#### Scenario: Worker 风险路由保持不变
- **WHEN** 桥接工具 execute_sandbox 被调用
- **THEN** 内部仍然走 SandboxWorker → E2B 隔离沙箱 → Pi Agent 的完整链路，风险隔离不变
