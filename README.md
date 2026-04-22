<div align="center">

# 🚀 Super Agent

**Enterprise-Grade Hybrid AI Agent Engine**

*Orchestrate complex workflows with Python, execute autonomously with sandboxed agents*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![Temporal](https://img.shields.io/badge/Temporal-Workflow-purple.svg)](https://temporal.io/)

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](./ARCHITECTURE.md)

</div>

---

## 🎯 Why Super Agent?

Building production-ready AI agents is hard. You need orchestration, safety, observability, and the ability to execute complex tasks autonomously. **Super Agent** solves this with a unique hybrid architecture:

- **🧠 Smart Orchestration**: Python-based control plane with PydanticAI for high-level planning
- **⚡ Autonomous Execution**: Sandboxed [pi coding agent](https://github.com/mariozechner/pi-coding-agent) for micro-level task execution
- **🔒 Zero-Trust Security**: E2B containerized sandboxes with temporary JWT tokens
- **📊 Full Observability**: Langfuse tracing + Temporal workflows + real-time metrics
- **🎨 Dynamic UI**: A2UI protocol - backend-driven component rendering
- **🔌 Extensible Skills**: Plugin system with 10+ pre-built skills

## ✨ Features

### 🏗️ Production-Ready Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React + A2UI Engine  │  Dynamic UI Rendering           │
├─────────────────────────────────────────────────────────┤
│  FastAPI Gateway      │  REST / WebSocket / SSE         │
├─────────────────────────────────────────────────────────┤
│  Temporal Workflows   │  Fault Tolerance + Retry        │
├─────────────────────────────────────────────────────────┤
│  PydanticAI Agent     │  Planning + Tool Routing        │
├──────────────────┬──────────────────────────────────────┤
│  Native Workers  │  Sandbox Workers (E2B + pi agent)   │
│  RAG / DB / API  │  Isolated Code Execution            │
├──────────────────┴──────────────────────────────────────┤
│  LiteLLM Proxy        │  Multi-Provider LLM Routing     │
├─────────────────────────────────────────────────────────┤
│  Langfuse             │  Tracing + Cost + Debugging     │
└─────────────────────────────────────────────────────────┘
```

### 🛡️ Security First

- **Control/Data Plane Isolation**: Business logic in Python, untrusted code in E2B containers
- **Temporary Credentials**: Sandboxes receive 10-min JWT tokens, never real API keys
- **SQL Injection Protection**: Whitelist-based query validation
- **Audit Trail**: Full request tracing with Langfuse

### 🎨 A2UI Protocol - Rethinking Agent UIs

Traditional agent UIs are static. **A2UI** (Agent-to-UI) is a protocol where the backend sends structured JSON instructions, and the frontend dynamically renders components:

```json
{
  "event_type": "render_widget",
  "ui_component": "DataChart",
  "props": {
    "type": "line",
    "data": [...],
    "title": "Patent Trend Analysis"
  }
}
```

**Benefits**:
- Backend controls UI logic (no frontend code changes for new visualizations)
- Streaming updates (SSE with resume support)
- Type-safe component contracts

### 🔌 Extensible Skill System

Skills are self-contained plugins with:
- Markdown documentation (auto-injected into agent context)
- Executable scripts (Python/Bash/JS)
- Progressive loading (summaries in prompt, full docs on-demand)

**Pre-built Skills**:
- 📄 Paper Search (semantic search via RAG)
- 🔍 Baidu AI Search
- 📊 Patent Trend Analysis
- 🎨 AI PPT Generator
- ...and more

### 🧪 Dual Sandbox Backends

| Mode | Use Case | Isolation | API Key |
|------|----------|-----------|---------|
| **Local** | Development | ❌ None | Direct host key |
| **E2B (Tencent)** | Production | ✅ Full container | Temporary JWT |

Switch with a single env var: `SANDBOX_PROVIDER=local|tencent`

### 📊 Built-in Observability

- **Temporal UI**: Workflow execution history, retry logs, state snapshots
- **Langfuse**: LLM call tracing, token costs, prompt debugging
- **Metrics API**:
  - `GET /api/agent/metrics/overview` - Step latency overview
  - `GET /api/agent/metrics/trace/{id}` - Full request timeline

### 🧩 Middleware Pipeline

Onion-model middleware for cross-cutting concerns:

```python
TokenUsage → LoopDetection → ToolErrorHandling →
  Summarization → Memory → [Agent Execution] →
    Memory → Summarization → ToolErrorHandling →
      LoopDetection → TokenUsage
```

- **Loop Detection**: Prevent infinite tool call cycles
- **Auto-Summarization**: Compress long conversation history
- **Memory Injection**: Retrieve user context from Redis
- **Token Tracking**: Log usage to Langfuse

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis
- [pi coding agent](https://github.com/mariozechner/pi-coding-agent): `npm install -g @mariozechner/pi-coding-agent`

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/super-agent-poc.git
cd super-agent-poc

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Key environment variables:

```bash
# LLM
OPENAI_API_KEY=sk-...
PLANNING_MODEL=claude-4.5-sonnet
EXECUTION_MODEL=claude-4.5-sonnet

# Sandbox
SANDBOX_PROVIDER=local  # Use 'local' for development
SANDBOX_PI_PROVIDER=openai
SANDBOX_PI_MODEL=gpt-4o

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: Langfuse tracing
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
```

### Run

```bash
# 安装前后端依赖
make install

# 同时启动前后端（推荐）
make dev

# 或分别启动
make dev-backend   # 后端 http://localhost:9001
make dev-frontend  # 前端 http://localhost:5173
```

其他命令：

```bash
make build   # 构建前端生产包
make lint    # 后端代码检查（ruff）
make help    # 查看所有命令
```

> 旧方式仍可用：`python run_deepagent.py` 启动后端，`cd frontend-deepagent && npm run dev` 启动前端。

Visit `http://localhost:5173` 🎉

### First Query

Try asking:
- "Search for recent papers on transformer architectures"
- "Analyze patent trends in AI chip design from 2020-2024"
- "Generate a PPT about quantum computing basics"

## 🏗️ Architecture

### Orchestration Pattern

**Super Agent** uses a **hybrid orchestration model**:

1. **Macro-level (Python)**: PydanticAI agent plans the overall workflow, routes tasks to workers
2. **Micro-level (pi agent)**: Autonomous ReAct loop inside sandboxes for code execution tasks

This separation provides:
- **Control**: Python orchestrator maintains global state and decision-making
- **Autonomy**: pi agent can iterate independently without round-trips
- **Safety**: Untrusted code execution is fully isolated

### Data Flow

```
User Input
  ↓
FastAPI Gateway (generate session_id)
  ↓
Temporal Workflow (fault-tolerant orchestration)
  ↓
PydanticAI Agent (planning + tool routing)
  ├─→ Native Workers (RAG, DB, API)
  └─→ Sandbox Workers (pi agent in E2B)
  ↓
Streaming Output (SSE with resume support)
  ↓
A2UI Engine (dynamic component rendering)
```

### Key Design Patterns

- **Orchestrator-Workers**: Centralized planning, distributed execution
- **Plan-and-Execute**: LLM generates DAG, execute in topological order
- **Onion Middleware**: Before/after hooks for cross-cutting concerns
- **Dual Backend Routing**: Transparent local/E2B switching
- **Progressive Loading**: Skill summaries in prompt, full docs on-demand
- **Server-Driven UI**: Backend controls frontend rendering

## 📚 Documentation

- [Full Architecture Guide](./ARCHITECTURE.md) - Deep dive into system design
- [Coding Style Guide](./CODING_STYLE_GUIDE.md) - Development conventions
- [Skill Development](./skill/README.md) - How to create custom skills

## 🧪 Testing

```bash
# Run all connectivity tests
pytest tests/test_connectivity.py -v -s

# Test specific components
pytest tests/test_connectivity.py::TestSkillConnectivity -v -s
pytest tests/test_connectivity.py::TestSandboxConnectivity -v -s
```

## 🛣️ Roadmap

- [ ] Multi-agent collaboration (agent-to-agent communication)
- [ ] Streaming DAG visualization in UI
- [ ] MCP (Model Context Protocol) server integration
- [ ] Voice input/output support
- [ ] Docker Compose one-click deployment
- [ ] Kubernetes Helm charts

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](./CONTRIBUTING.md) first.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- [PydanticAI](https://github.com/pydantic/pydantic-ai) - Type-safe agent framework
- [pi coding agent](https://github.com/mariozechner/pi-coding-agent) - Autonomous coding agent
- [Temporal](https://temporal.io/) - Durable workflow engine
- [E2B](https://e2b.dev/) - Secure code execution sandboxes
- [Langfuse](https://langfuse.com/) - LLM observability platform

---

<div align="center">

**If you find this project useful, please consider giving it a ⭐!**

[Report Bug](https://github.com/yourusername/super-agent-poc/issues) • [Request Feature](https://github.com/yourusername/super-agent-poc/issues)

</div>
