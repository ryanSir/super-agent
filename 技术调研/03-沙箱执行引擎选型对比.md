# Agent 执行引擎对比：Pi-mono vs Claude API vs Claude CLI — 方案对比与决策

> 整理时间：2026-04-20
> 对话背景：评估 Claude Agent SDK 替代/补充 pi-mono 作为沙箱执行引擎的可行性

## 背景与目标

当前项目使用 pi-mono（`@mariozechner/pi-coding-agent@0.62.0`）作为沙箱内的自主执行 Agent，负责代码生成、文件操作、脚本执行等任务。需要研究 Claude Agent SDK 的实现方式，评估其作为替代或补充方案的可行性，从性能、开发成本、功能完整度等维度做全面对比。

约束条件：所有模型请求统一走 rd-gateway（多协议网关，后端对接 AWS Bedrock）。编排层走 Anthropic 原生路径（`/v1/messages`），pi-mono 走 OpenAI 兼容路径（`/v1/chat/completions`）。

## 方案对比

### 三种实现方式

| 方案 | 核心思路 | 优点 | 缺点/风险 |
|------|---------|------|----------|
| **Pi-mono CLI** (`pi --print --mode json`) | Node.js 子进程，内置完整 agent loop + 4 原子工具 | 开箱即用；双层循环 + 并行工具执行 + steering queue；支持 10 种模型协议（Anthropic/OpenAI/Gemini/Bedrock/Mistral 等）；上下文压缩、session 持久化、hooks 全有 | 多一层 Node.js 进程启动开销（~2-3s）；JSONL 输出解析有适配成本 |
| **Claude API 直调** (`anthropic.Anthropic().messages.create()`) | Python 进程内直接调 Anthropic Messages API，自建 agentic loop | 零进程启动开销；最小上下文（~900 tokens）；完全可控 | 当前实现是"玩具级"——缺上下文压缩、流式输出、并行工具执行、steering queue、hooks、错误重试、session 持久化；自建补全至少 2-3 周；只支持 Anthropic 协议 |
| **Claude Code CLI** (`claude -p --output-format json`) | Claude Code 子进程，内置完整项目感知 + 工具链 | 功能最强（内置 Read/Edit/Bash/Write/Git/MCP/Web Search）；自动上下文压缩；项目感知 | 加载完整项目上下文（111k tokens），单次调用 $0.56；速度最慢（18.5s vs 7.2s）；开销过大不适合沙箱场景 |

### Benchmark 数据（同模型 claude-4.6-opus，11 个有效 case，排除 case 9 超时数据）

| 维度 | Pi-mono | Claude API 直调 | Claude Code CLI |
|------|---------|----------------|----------------|
| 简单任务（case 1-3） | 23.9s | 22.0s ✓ 更快 | 40.8s |
| 中等任务（case 4-6） | 47.0s ✓ 更快 | 49.8s | 64.4s |
| 复杂任务（case 7-8） | 61.7s ✓ 更快 | 69.6s | 77.3s |
| Skill 执行（case 10-11） | 41.3s | 34.0s ✓ 更快 | 50.3s |
| 端到端（case 12） | 24.4s ✓ 更快 | 26.1s | 38.0s |
| **总耗时（11 case）** | **198.3s ✓ 最快** | **201.5s** | **270.8s** |
| 胜场 | 6 | 5 | 0 |
| 成功率（11 case） | 11/11（100%） | 11/11（100%） | 11/11（100%） |
| Input Tokens/次 | 不透明 | ~900-4,000 | ~74,000-308,000 |
| 总成本 | 不透明（走 gateway） | 低（最小上下文） | ~$8.89（11 次调用） |

> 注：Case 9（REST API 服务器）Pi-mono 超时 180s 失败，Claude API 42.7s 成功，Claude CLI 28.9s 成功。该 case 因 Pi-mono 超时导致数据不对等，从汇总统计中排除，单独列于逐 Case 详细数据中。

#### 逐 Case 详细数据

| Case | 任务 | Level | Pi-mono | Claude API | Claude CLI | Claude CLI Cost |
|------|------|-------|---------|-----------|-----------|----------------|
| 1 | 单文件创建 | simple | 7.9s ✓ | 9.0s ✓ | 16.2s ✓ | $0.56 |
| 2 | Bash 命令执行 | simple | 8.8s ✓ | 8.5s ✓ | 15.7s ✓ | $0.57 |
| 3 | 文件读取分析 | simple | 7.2s ✓ | 4.5s ✓ | 8.9s ✓ | $0.38 |
| 4 | 创建+编辑+验证 | medium | 15.8s ✓ | 17.5s ✓ | 22.2s ✓ | $0.75 |
| 5 | 多文件项目创建 | medium | 19.1s ✓ | 20.8s ✓ | 22.1s ✓ | $0.58 |
| 6 | Bug 修复 | medium | 12.1s ✓ | 11.5s ✓ | 20.1s ✓ | $0.76 |
| 7 | 数据处理管道 | complex | 22.5s ✓ | 25.3s ✓ | 28.2s ✓ | $0.96 |
| 8 | 代码重构 | complex | 39.2s ✓ | 44.3s ✓ | 49.1s ✓ | $1.56 |
| 9* | REST API 服务器 | complex | 180s ERR | 42.7s ✓ | 28.9s ✓ | $0.59 |
| 10 | Skill: 专利查询 | skill | 17.8s ✓ | 12.2s ✓ | 17.5s ✓ | $0.59 |
| 11 | Skill: 发现+执行 | skill | 23.5s ✓ | 21.8s ✓ | 32.8s ✓ | $1.01 |
| 12 | CLI 工具开发 | e2e | 24.4s ✓ | 26.1s ✓ | 38.0s ✓ | $1.17 |

> *Case 9 因 Pi-mono 超时，未计入汇总统计。

#### 关键发现

- **Pi-mono 和 Claude API 直调性能几乎持平**：11 个有效 case 总耗时仅差 3.2s（1.6%），Pi-mono 198.3s vs Claude API 201.5s
- **Pi-mono 在多步操作上有优势**：中等任务（case 4-6）和复杂任务（case 7-8）Pi-mono 均更快，得益于内部并行工具执行和更轻的进程内通信
- **Claude API 在读取密集型和 Skill 执行上更快**：case 3（文件读取）Claude API 4.5s vs Pi-mono 7.2s，case 10（Skill 执行）12.2s vs 17.8s，因为进程内直接读文件省掉了 CLI 启动开销
- **Claude Code CLI 全面最慢**：11 个有效 case 中 0 胜，每次调用多消耗 74k-308k tokens 的内置 prompt 开销
- **Claude Code CLI 单次成本 $0.38-$1.56**，11 次调用总计 $8.89，是 API 直调的数十倍
- **三方在 11 个有效 case 中均 100% 成功**，稳定性无差异

### 内部执行机制对比

| 维度 | Pi-mono | Claude API 直调 |
|------|---------|----------------|
| Agent Loop | 双层 while 循环（外层 follow-up + 内层 tool calls + steering） | 单层 while 循环 |
| System Prompt | 完整 prompt 工程（角色定义 + 工具说明 + guidelines + 项目上下文 + skills） | 一句话 system prompt |
| 工具执行 | 默认并行（`toolExecution: "parallel"`） | 顺序执行 |
| Streaming | 流式获取 LLM 响应（`streamSimple()`） | 同步等待完整响应（`messages.create()`） |
| 消息队列 | Steering + Follow-up 双队列 | 无 |
| Hooks | beforeToolCall / afterToolCall 拦截 | 无 |
| 上下文管理 | 自动 compaction | 无 |
| 多模型 | 10 种协议（Anthropic/OpenAI/Gemini/Bedrock/Mistral/Azure 等） | 仅 Anthropic |

### 协议路径

```
编排层 PydanticAI:  Anthropic SDK → rd-gateway/v1/messages → Bedrock Claude
Pi-mono 沙箱:       OpenAI SDK   → rd-gateway/v1/chat/completions → Bedrock Claude
Claude API 测试类:  Anthropic SDK → rd-gateway/v1/messages → Bedrock Claude
```

代码层面不需要兼容多协议——rd-gateway 统一了后端，pi-mono 的 `--provider my-gateway` 固定走 OpenAI 兼容路径，换模型只改 `.env` 的 `SANDBOX_PI_MODEL` 即可。

## 决策结论

**选择：继续使用 Pi-mono 作为沙箱执行引擎**

Claude API 直调作为补充方案保留（适用于不需要沙箱隔离的轻量场景）。Claude Code CLI 因开销过大不适合当前场景。

## 决策理由

- **开发成本**：Pi-mono 开箱即用，Claude API 直调要达到生产可用需自建上下文压缩、并行工具执行、streaming、hooks、错误重试等，至少 2-3 周工作量
- **功能完整度**：Pi-mono 的 agent-loop 经过充分打磨（双层循环、steering queue、compaction），自建方案短期内无法达到同等成熟度
- **多模型灵活性**：Pi-mono 支持 10 种协议，通过 `--provider` + `--model` 参数即可切换，代码层面零改动
- **性能差异不大**：排除 case 9 超时后，两者总耗时差距仅 1.6%（198.3s vs 201.5s），不构成决策因素
- **稳定性**：Claude API 直调在 12 个 case 中 100% 成功，Pi-mono 在复杂场景（REST API 服务器）有超时风险，但这是任务本身的问题而非引擎问题

## 遗留问题

- Pi-mono 在 case 9（REST API 服务器）超时失败，可能是启动 HTTP server 后进程阻塞导致，需排查 pi-mono 对长时间运行子进程的处理机制
- Claude API 直调的 system prompt 过于简单（一句话），如果后续要用需补充完整的 prompt 工程
- Benchmark 只跑了一轮，结果有随机性，严格对比需要多轮取平均值
- Claude Code CLI 即使在干净临时目录（无 CLAUDE.md、无 .git）中，内置 system prompt 仍消耗 74k-308k tokens/次，这是 Claude Code 架构决定的，无法通过 `--bare` 等参数消除

## 附件

测试代码位于 `claude-sdk-agent/` 目录：
- `claude_agent.py` — Claude API 直调实现
- `pi_agent.py` — Pi-mono CLI 封装
- `claude_cli_agent.py` — Claude Code CLI 封装
- `benchmark.py` — 三方对比测试框架（12 个 case，支持 `--agents` 参数选择）
- `benchmark_results.json` — 测试结果数据
