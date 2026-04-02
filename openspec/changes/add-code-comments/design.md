## Context

项目是一个企业级混合智能体核心引擎 POC，采用 Orchestrator-Workers 架构，包含 Python 后端（FastAPI + PydanticAI）、React 前端、Skill 插件系统。项目开发已完成，进入 code review 阶段，需要添加结构化注释以降低理解成本。

当前代码状态：
- `src/` 下约 14 个子模块、50+ Python 文件，部分模块缺少模块级 docstring
- `frontend/src/` 下约 15 个 TypeScript/TSX 文件，缺少 JSDoc 注释
- `skill/` 下 3 个技能包的脚本缺少功能说明

## Goals / Non-Goals

**Goals:**
- 为每个 Python 模块添加模块级 docstring，说明职责和架构位置
- 为核心类和公开方法添加参数/返回值/行为说明的 docstring
- 在复杂逻辑处添加行内注释，解释设计决策（"为什么"而非"做什么"）
- 为前端核心组件和引擎模块添加 JSDoc 注释
- 为 Skill 脚本添加功能说明

**Non-Goals:**
- 不修改任何代码逻辑或行为
- 不为 tests/ 下的测试文件添加注释
- 不为简单的 getter/setter、__init__ 赋值等显而易见的代码添加注释
- 不添加 TODO/FIXME 标记

## Decisions

### 1. 注释语言：中文注释 + 英文变量名

保持项目现有约定（Language: 中文注释，英文变量名）。docstring 和行内注释使用中文，代码标识符保持英文。

### 2. 注释分层策略

按优先级分三层处理：

| 层级 | 范围 | 注释类型 | 说明 |
|------|------|----------|------|
| L1 模块级 | 每个 .py / .ts 文件顶部 | 模块 docstring / 文件头注释 | 说明模块职责、在架构中的位置、关键依赖 |
| L2 类/函数级 | 核心类和公开方法 | docstring / JSDoc | 说明参数、返回值、异常、关键行为 |
| L3 行内级 | 复杂逻辑段落 | 行内注释 | 解释设计决策、算法选择、边界处理的原因 |

### 3. 按架构层分批处理

按项目架构层从底向上添加注释，确保每层的注释可以引用下层的概念：

1. **基础层**：config、core、schemas
2. **数据层**：memory、llm、mcp
3. **执行层**：workers（native + sandbox）
4. **编排层**：orchestrator、middleware、state
5. **接入层**：gateway、streaming、monitoring
6. **技能层**：skills
7. **前端层**：engine → components

### 4. Python docstring 格式：Google Style

```python
def plan_tasks(query: str, context: dict) -> DAGPlan:
    """根据用户查询生成 DAG 任务拓扑。

    通过 LLM 分析用户意图，将复杂查询拆解为可并行执行的任务节点，
    生成有向无环图（DAG）作为执行计划。

    Args:
        query: 用户原始查询文本
        context: 包含会话历史和用户画像的上下文

    Returns:
        DAGPlan: 包含 TaskNode 列表和依赖关系的执行计划

    Raises:
        PlanningError: LLM 返回无效的 DAG 结构时抛出
    """
```

### 5. TypeScript 注释格式：JSDoc

```typescript
/**
 * SSE 客户端 - 负责与后端建立 Server-Sent Events 连接
 *
 * 支持断点续传：通过 Last-Event-ID 头实现连接恢复后的消息补发。
 * 内部维护重连逻辑，指数退避策略避免服务端过载。
 */
```

## Risks / Trade-offs

- **[注释过时风险]** → 注释仅描述设计意图和"为什么"，避免重复代码逻辑（"做什么"），降低注释与代码不同步的概率
- **[注释噪音]** → 严格遵循"不为显而易见的代码添加注释"原则，只在复杂逻辑和设计决策处添加
- **[大量文件变更]** → 按架构层分批提交，每批可独立 review，降低单次 review 负担