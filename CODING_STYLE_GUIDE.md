# Eureka Agent 编码规范指南

## 目录
- [规范优先级](#规范优先级)
- [1. 主流程优先原则](#1-主流程优先原则)
- [2. 高内聚、低耦合](#2-高内聚低耦合)
- [3. 类型注解](#3-类型注解)
- [4. 结构化日志](#4-结构化日志)
- [5. 异常处理](#5-异常处理)
- [6. 性能监控](#6-性能监控)
- [7. 文档规范](#7-文档规范)
- [8. 命名规范](#8-命名规范)
- [9. 代码组织](#9-代码组织)
- [代码审查检查清单](#代码审查检查清单)
- [工具配置](#工具配置)

---

## 规范优先级

### P0（强制要求）
- 主流程优先原则
- 高内聚、低耦合
- 公开 API 类型注解
- 结构化日志
- 异常处理

### P1（强烈推荐）
- 性能监控
- 文档规范（公开 API）
- 命名规范

### P2（建议遵循）
- 代码组织
- 私有方法文档

---

## 1. 主流程优先原则

### 核心理念
公开方法应该像"目录"一样，让读者一眼看出主流程的 3-7 个关键步骤，细节抽取为私有方法。

### 规则
- **单个方法不超过 50 行**（复杂流程不超过 80 行）
- **公开方法展示主流程**（3-7 步）
- **细节抽取为私有方法**（以 `_` 开头）
- **避免深层嵌套**（最多 2-3 层）

### ❌ 反例：主流程被细节淹没

```python
async def execute_query(self, query: str, session_id: str) -> Dict[str, Any]:
    """执行查询 - 主流程被细节淹没，难以理解"""
    # 验证输入
    if not query or not query.strip():
        raise ValueError("查询不能为空")
    if len(query) > 10000:
        raise ValueError("查询过长")

    # 获取会话
    session = await self.session_manager.get_session(session_id)
    if not session:
        session = await self.session_manager.create_session(session_id)

    # 理解意图
    intent_result = await self.intent_analyzer.analyze(query)
    if intent_result.confidence < 0.5:
        logger.warning(f"意图识别置信度低: {intent_result.confidence}")

    # 规划任务
    tasks = []
    for intent in intent_result.intents:
        if intent.type == "search":
            task = SearchTask(query=intent.query, filters=intent.filters)
        elif intent.type == "analyze":
            task = AnalyzeTask(query=intent.query, method=intent.method)
        tasks.append(task)

    # 执行任务
    results = []
    for task in tasks:
        try:
            result = await self.executor.execute(task)
            results.append(result)
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            results.append({"error": str(e)})

    # 生成响应
    response = await self.response_generator.generate(results)
    return response
```

### ✅ 正例：主流程清晰

```python
async def execute_query(self, query: str, session_id: str) -> Dict[str, Any]:
    """执行查询 - 主流程清晰，一目了然"""
    # 1. 验证和准备
    self._validate_query(query)
    session = await self._get_or_create_session(session_id)

    # 2. 理解意图
    intent_result = await self._analyze_intent(query)

    # 3. 规划任务
    tasks = self._plan_tasks(intent_result)

    # 4. 执行任务
    results = await self._execute_tasks(tasks)

    # 5. 生成响应
    return await self._generate_response(results)

def _validate_query(self, query: str) -> None:
    """验证查询输入"""
    if not query or not query.strip():
        raise ValueError("查询不能为空")
    if len(query) > 10000:
        raise ValueError("查询过长")

async def _get_or_create_session(self, session_id: str) -> Session:
    """获取或创建会话"""
    session = await self.session_manager.get_session(session_id)
    if not session:
        session = await self.session_manager.create_session(session_id)
    return session
```

---

## 2. 高内聚、低耦合

### 核心理念
每个类应该只有一个职责，类之间通过接口（Protocol）交互，使用依赖注入而非类内创建依赖。

### 规则
- **单一职责**：每个类只做一件事
- **接口隔离**：使用 Protocol 定义接口
- **依赖注入**：通过构造函数注入依赖
- **避免类内创建依赖**：不在类内 `new` 其他类

### ❌ 反例：低内聚、高耦合

```python
class QueryHandler:
    """职责混乱，耦合严重"""

    def __init__(self):
        # 类内创建依赖 - 高耦合
        self.intent_analyzer = IntentAnalyzer()
        self.task_planner = TaskPlanner()
        self.executor = TaskExecutor()
        self.response_generator = ResponseGenerator()

    async def handle(self, query: str) -> str:
        # 混合了意图分析、任务规划、执行、响应生成
        intent = await self.intent_analyzer.analyze(query)
        tasks = self.task_planner.plan(intent)
        results = await self.executor.execute(tasks)
        return self.response_generator.generate(results)
```

### ✅ 正例：高内聚、低耦合

```python
from typing import Protocol

# 定义接口
class IntentAnalyzer(Protocol):
    async def analyze(self, query: str) -> IntentResult: ...

class TaskPlanner(Protocol):
    def plan(self, intent: IntentResult) -> List[Task]: ...

class TaskExecutor(Protocol):
    async def execute(self, tasks: List[Task]) -> List[Result]: ...

# 单一职责的类
class QueryOrchestrator:
    """查询编排器 - 只负责协调流程"""

    def __init__(
        self,
        intent_analyzer: IntentAnalyzer,
        task_planner: TaskPlanner,
        executor: TaskExecutor
    ):
        # 依赖注入 - 低耦合
        self.intent_analyzer = intent_analyzer
        self.task_planner = task_planner
        self.executor = executor

    async def orchestrate(self, query: str) -> List[Result]:
        """编排查询流程"""
        intent = await self.intent_analyzer.analyze(query)
        tasks = self.task_planner.plan(intent)
        return await self.executor.execute(tasks)
```

---

## 3. 类型注解

### 核心理念
类型注解是代码的"合同"，让 IDE 和工具能够提供更好的支持，也让代码更易理解。

### 规则
- **公开 API 必须有类型注解**（P0）
- **私有方法推荐有类型注解**（P1）
- **使用 TypedDict 定义复杂字典结构**
- **使用 Protocol 定义接口**

### ❌ 反例：缺少类型注解

```python
async def execute_query(self, query, session_id):
    """缺少类型注解，IDE 无法提供帮助"""
    result = await self._process(query)
    return result

def _process(self, query):
    # 返回值类型不明确
    return {"status": "ok", "data": query}
```

### ✅ 正例：完整类型注解

```python
from typing import TypedDict

class QueryResult(TypedDict):
    """查询结果结构"""
    status: str
    data: str
    metadata: Dict[str, Any]

async def execute_query(
    self,
    query: str,
    session_id: str
) -> QueryResult:
    """执行查询 - 类型清晰"""
    result = await self._process(query)
    return result

def _process(self, query: str) -> QueryResult:
    """处理查询"""
    return {
        "status": "ok",
        "data": query,
        "metadata": {}
    }
```

---

## 4. 结构化日志

### 核心理念
日志应该既易于人类阅读，又易于机器解析。使用中文描述 + 结构化参数。

### 规则
- **格式**：`logger.info(f"[模块] 描述 | key=value")`
- **使用中文描述**：便于快速理解
- **结构化参数**：便于日志分析
- **关键路径必须有日志**

### ❌ 反例：非结构化日志

```python
logger.info(f"开始执行查询: {query}")
logger.info(f"意图分析结果: {intent_result}")
logger.error(f"执行失败: {str(e)}")
```

### ✅ 正例：结构化日志

```python
logger.info(f"[QueryHandler] 开始执行查询 | query_len={len(query)} session_id={session_id}")
logger.info(f"[IntentAnalyzer] 意图分析完成 | confidence={intent_result.confidence} intent_type={intent_result.type}")
logger.error(f"[TaskExecutor] 任务执行失败 | task_id={task.id} error={str(e)}", exc_info=True)
```

---

## 5. 异常处理

### 核心理念
异常处理应该明确、具体，包含足够的上下文信息，便于问题定位。

### 规则
- **捕获具体异常**：避免 `except Exception`
- **包含上下文信息**：记录关键参数
- **保留异常链**：使用 `raise ... from e`
- **关键路径必须有异常处理**

### ❌ 反例：模糊的异常处理

```python
async def execute_task(self, task):
    try:
        result = await self.executor.execute(task)
        return result
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return None
```

### ✅ 正例：明确的异常处理

```python
async def execute_task(self, task: Task) -> TaskResult:
    """执行任务"""
    try:
        result = await self.executor.execute(task)
        return result
    except TimeoutError as e:
        logger.error(
            f"[TaskExecutor] 任务执行超时 | "
            f"task_id={task.id} task_type={task.type} timeout={task.timeout}",
            exc_info=True
        )
        raise TaskExecutionError(f"任务 {task.id} 执行超时") from e
    except ValidationError as e:
        logger.error(
            f"[TaskExecutor] 任务参数验证失败 | "
            f"task_id={task.id} error={str(e)}",
            exc_info=True
        )
        raise TaskValidationError(f"任务 {task.id} 参数无效") from e
    except Exception as e:
        logger.error(
            f"[TaskExecutor] 任务执行失败 | "
            f"task_id={task.id} error_type={type(e).__name__}",
            exc_info=True
        )
        raise TaskExecutionError(f"任务 {task.id} 执行失败: {str(e)}") from e
```

---

## 6. 性能监控

### 核心理念
关键路径必须有性能监控，便于发现性能瓶颈。

### 规则
- **使用 StopWatch 监控关键路径**
- **在完成时打印 `sw.pretty_print()`**
- **记录关键步骤的耗时**

### ✅ 示例

```python
from app.common.stopwatch import StopWatch

async def execute_query(self, query: str, session_id: str) -> Dict[str, Any]:
    """执行查询"""
    sw = StopWatch()

    # 1. 理解意图
    intent_result = await self._analyze_intent(query)
    sw.lap("意图分析")

    # 2. 规划任务
    tasks = self._plan_tasks(intent_result)
    sw.lap("任务规划")

    # 3. 执行任务
    results = await self._execute_tasks(tasks)
    sw.lap("任务执行")

    # 4. 生成响应
    response = await self._generate_response(results)
    sw.lap("响应生成")

    # 打印性能报告
    logger.info(f"[QueryHandler] 查询完成\n{sw.pretty_print()}")
    return response
```

---

## 7. 文档规范

### 核心理念
公开 API 必须有清晰的文档，说明功能、参数、返回值。

### 规则
- **公开 API 必须有 docstring**（P1）
- **说明功能、参数、返回值**
- **包含使用示例（复杂 API）**
- **私有方法推荐有简短说明**

### ✅ 示例

```python
async def execute_query(
    self,
    query: str,
    session_id: str,
    mode: str = "react"
) -> QueryResult:
    """执行查询

    Args:
        query: 用户查询文本
        session_id: 会话 ID
        mode: 执行模式，可选值: "react", "plan_and_solve", "direct"

    Returns:
        QueryResult: 查询结果，包含 status、data、metadata

    Raises:
        ValueError: 查询参数无效
        TaskExecutionError: 任务执行失败

    Example:
        >>> result = await handler.execute_query(
        ...     query="查找锂电池专利",
        ...     session_id="session_123",
        ...     mode="react"
        ... )
    """
    pass
```

---

## 8. 命名规范

### 核心理念
命名应该清晰、一致、符合 Python 社区惯例。

### 规则
- **类名**：PascalCase（如 `QueryHandler`）
- **函数/方法名**：snake_case（如 `execute_query`）
- **常量**：UPPER_SNAKE_CASE（如 `MAX_RETRY_COUNT`）
- **私有方法**：以 `_` 开头（如 `_validate_input`）
- **布尔变量**：使用 `is_`、`has_`、`can_` 前缀
- **避免缩写**：除非是广泛认可的（如 `id`、`url`）

### ✅ 示例

```python
class QueryHandler:
    MAX_QUERY_LENGTH = 10000  # 常量

    def __init__(self):
        self.is_initialized = False  # 布尔变量
        self.has_cache = True

    async def execute_query(self, query: str) -> QueryResult:
        """公开方法"""
        return await self._process_query(query)

    def _process_query(self, query: str) -> QueryResult:
        """私有方法"""
        pass
```

---

## 9. 代码组织

### 核心理念
代码应该按照逻辑分组，便于查找和维护。

### 规则

#### 导入顺序（P0 强制）
- **标准库** → **第三方库** → **本地模块**
- 每组之间用**空行**分隔
- 每组内按字母顺序排序
- `TYPE_CHECKING` 导入放在本地模块之后

**详细规则**：
1. **标准库**：Python 内置模块（如 `asyncio`, `logging`, `typing`）
2. **第三方库**：通过 pip 安装的外部包（如 `fastapi`, `pydantic`, `django`）
3. **本地模块**：项目内部模块（如 `app.eureka_agent.*`, `core.*`）
4. **TYPE_CHECKING 块**：类型检查专用导入，避免循环依赖

#### 类内方法顺序
  1. `__init__`
  2. 公开方法（按调用顺序）
  3. 私有方法（按调用顺序）

#### 相关代码放在一起

### ✅ 正例：标准导入顺序

```python
# 标准库
import asyncio
import logging
from typing import Dict, List, Protocol, TYPE_CHECKING

# 第三方库
from fastapi import APIRouter
from pydantic import BaseModel

# 本地模块
from app.eureka_agent.agent.react_agent import ReactAgent
from app.eureka_agent.api.schemas import QueryRequest
from core.utils.logger import logger

# TYPE_CHECKING 导入（避免循环依赖）
if TYPE_CHECKING:
    from app.eureka_agent.utils.stopwatch import StopWatch


class QueryHandler:
    """查询处理器"""

    def __init__(self, agent: ReactAgent):
        self.agent = agent

    # 公开方法
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """执行查询"""
        intent = await self._analyze_intent(query)
        return await self._execute_with_intent(intent)

    # 私有方法
    async def _analyze_intent(self, query: str) -> Intent:
        """分析意图"""
        pass

    async def _execute_with_intent(self, intent: Intent) -> Dict[str, Any]:
        """根据意图执行"""
        pass
```

---

## 代码审查检查清单

### P0（必须检查）
- [ ] 主流程清晰，细节已抽取为私有方法
- [ ] 单个方法不超过 50 行（复杂流程不超过 80 行）
- [ ] 类职责单一（高内聚）
- [ ] 使用依赖注入，而非类内创建依赖（低耦合）
- [ ] 公开 API 有完整类型注解
- [ ] 使用结构化日志（`[模块] 描述 | key=value`）
- [ ] 异常处理明确，包含上下文信息
- [ ] 使用 `raise ... from e` 保留异常链

### P1（强烈推荐）
- [ ] 关键路径有 StopWatch 监控
- [ ] 公开 API 有 docstring
- [ ] 命名清晰、一致
- [ ] 代码按逻辑分组

### P2（建议检查）
- [ ] 私有方法有简短说明
- [ ] 导入顺序正确
- [ ] 相关代码放在一起

---

## 工具配置

### 代码检查

```bash
# 运行 flake8 + pylint
make lint

# 语法检查
make compile
```

### 代码格式化

```bash
# 使用 black 格式化（使用默认配置）
black app/eureka_agent/

# 格式化单个文件
black app/eureka_agent/api/query_conversational.py
```

### IDE 配置

推荐使用 PyCharm 或 VS Code，配置：
- 启用类型检查
- 启用自动格式化（black）
- 启用 import 排序（isort）

---

## 实施建议

### 对于新代码
- 严格遵循 P0 规范
- 尽量遵循 P1 规范
- 参考 P2 规范

### 对于旧代码
- 修改时逐步改进
- 优先修复 P0 问题
- 不强制全部重构

### 代码审查重点
1. 主流程是否清晰？
2. 类职责是否单一？
3. 是否使用依赖注入？
4. 公开 API 是否有类型注解？
5. 日志是否结构化？
6. 异常处理是否明确？

---

