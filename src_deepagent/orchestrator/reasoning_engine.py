"""推理引擎 — ReasoningEngine

合并意图理解 + 复杂度评估 + 执行模式决策 + 工具资源获取。
两阶段流水线：Reason → Execute。
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from src_deepagent.core.exceptions import ReasoningError
from src_deepagent.core.logging import get_logger

logger = get_logger(__name__)


# ── 枚举与数据类 ─────────────────────────────────────────


class ExecutionMode(str, enum.Enum):
    """执行模式"""

    DIRECT = "direct"
    AUTO = "auto"
    PLAN_AND_EXECUTE = "plan_and_execute"
    SUB_AGENT = "sub_agent"


class ComplexityLevel(str, enum.Enum):
    """复杂度等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


_LEVEL_TO_MODE: dict[ComplexityLevel, ExecutionMode] = {
    ComplexityLevel.LOW: ExecutionMode.DIRECT,
    ComplexityLevel.MEDIUM: ExecutionMode.AUTO,
    ComplexityLevel.HIGH: ExecutionMode.SUB_AGENT,
    ComplexityLevel.VERY_HIGH: ExecutionMode.SUB_AGENT,
}


@dataclass(frozen=True)
class ComplexityScore:
    """复杂度评估结果"""

    level: ComplexityLevel
    score: float
    dimensions: dict[str, float]
    suggested_mode: ExecutionMode


@dataclass(frozen=True)
class ResolvedResources:
    """一次获取的工具资源，整个请求生命周期内共享"""

    workers: dict[str, Any]
    mcp_toolsets: list[Any]
    skill_summary: str
    bridge_tools: list[Callable]
    deferred_tool_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionPlan:
    """推理引擎输出"""

    mode: ExecutionMode
    complexity: ComplexityScore
    prompt_prefix: str
    resources: ResolvedResources


# ── 规则匹配模式 ─────────────────────────────────────────

# 中文 direct 触发：单一动作 + 明确对象
_DIRECT_PATTERNS_ZH = [
    re.compile(
        r"(写|实现|编写|生成|创建|开发).{0,10}"
        r"(代码|算法|脚本|程序|函数|类|模块|工具|爬虫|排序|服务)"
    ),
    re.compile(
        r"(搜索|检索|查找|查询|搜一下|找).{0,10}"
        r"(论文|专利|文献|文档|资料|数据)"
    ),
    re.compile(r"(翻译|总结|解释|概括|摘要|改写|润色)"),
    re.compile(r"(画|绘制|生成).{0,6}(图表|图|表格|PPT|幻灯片)"),
]

# 英文 direct 触发
_DIRECT_PATTERNS_EN = [
    re.compile(
        r"(write|implement|create|build|develop|code|generate)\s.{0,20}"
        r"(script|code|function|class|algorithm|program|tool|sorter|crawler|service)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(search|find|look\s?up|query|retrieve)\s.{0,20}"
        r"(paper|patent|document|article|literature)",
        re.IGNORECASE,
    ),
    re.compile(r"(translate|summarize|explain|paraphrase|rewrite)", re.IGNORECASE),
]

# 中文 plan 触发：多步骤连接词
_PLAN_PATTERNS_ZH = [
    re.compile(r"(先|首先).{2,30}(再|然后|接着|之后).{2,30}(最后|最终|并且)?"),
    re.compile(r".{2,20}(并且|同时|以及).{2,20}(并且|同时|以及|然后|再)"),
    re.compile(
        r"(检索|搜索|查询).{2,20}(分析|对比|比较)"
        r".{0,20}(生成|展示|可视化|输出|报告)?"
    ),
    re.compile(
        r"(对比|比较|分析).{2,20}(趋势|变化|差异)"
        r".{0,20}(图表|可视化|报告)?"
    ),
]

# 英文 plan 触发
_PLAN_PATTERNS_EN = [
    re.compile(
        r"(first|start\sby).{5,40}(then|next|after\sthat).{5,40}(finally|lastly)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(search|retrieve|fetch).{5,30}(analyze|compare)"
        r".{0,30}(generate|visualize|report)?",
        re.IGNORECASE,
    ),
]

# ── Prompt 前缀 ──────────────────────────────────────────

_PLAN_EXECUTE_PREFIX = (
    "[执行模式: plan_and_execute] "
    "这是一个复杂的多步骤任务，请先调用 plan_and_decompose 进行任务规划，"
    "然后按照 DAG 拓扑顺序逐步执行各子任务。\n\n"
)

_SUB_AGENT_PREFIX = (
    "[执行模式: sub_agent] "
    "这是一个复杂的多步骤任务，需要多个专业 Sub-Agent 协作完成。\n"
    "请先调用 plan_and_decompose 进行任务规划，然后使用 task() "
    "将各子任务分配给合适的 Sub-Agent。\n"
    "可用的 Sub-Agent:\n"
    "- researcher: 信息检索与综合分析专家\n"
    "- analyst: 数据分析与可视化专家\n"
    "- writer: 报告与文档撰写专家\n\n"
)

_DIRECT_TOOL_BLACKLIST = frozenset(["plan_and_decompose"])


# ── 复杂度评估关键词 ─────────────────────────────────────

# 领域关键词（用于 domain_span 评估）
_DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "research": {"搜索", "检索", "论文", "文献", "调研", "search", "research", "paper"},
    "analysis": {"分析", "对比", "比较", "趋势", "统计", "analyze", "compare", "trend"},
    "coding": {"代码", "脚本", "编程", "算法", "实现", "code", "script", "implement"},
    "visualization": {"图表", "可视化", "绘制", "展示", "chart", "visualize", "plot"},
    "writing": {"报告", "文档", "撰写", "PPT", "总结", "report", "document", "write"},
    "data": {"数据", "数据库", "查询", "SQL", "data", "database", "query"},
}

# 输出类型关键词（用于 output_complexity 评估）
_OUTPUT_KEYWORDS: dict[str, float] = {
    "报告": 0.9, "report": 0.9,
    "PPT": 0.9, "幻灯片": 0.9, "presentation": 0.9,
    "文档": 0.8, "document": 0.8,
    "图表": 0.7, "chart": 0.7, "可视化": 0.7, "visualization": 0.7,
    "列表": 0.4, "list": 0.4,
    "摘要": 0.5, "summary": 0.5,
}

# 推理深度关键词（用于 reasoning_depth 评估）
_REASONING_KEYWORDS: dict[str, float] = {
    "对比分析": 0.9, "综合评估": 0.9, "深度分析": 0.9,
    "compare": 0.9, "evaluate": 0.9,
    "分析": 0.7, "analyze": 0.7, "assess": 0.7,
    "综合": 0.6, "synthesize": 0.6,
    "搜索": 0.3, "search": 0.3, "检索": 0.3, "retrieve": 0.3,
    "翻译": 0.2, "translate": 0.2,
}


# ── ReasoningEngine ──────────────────────────────────────


class ReasoningEngine:
    """推理引擎

    合并意图理解 + 复杂度评估 + 执行模式决策 + 工具资源获取。
    两阶段流水线：Reason → Execute。
    """

    # 复杂度评估维度权重
    WEIGHTS: dict[str, float] = {
        "task_count": 0.25,
        "domain_span": 0.20,
        "dependency_depth": 0.20,
        "output_complexity": 0.15,
        "reasoning_depth": 0.20,
    }

    def __init__(self, workers: dict[str, Any]) -> None:
        self._workers = workers
        self._resources_cache: ResolvedResources | None = None

    # ── 公开接口 ──────────────────────────────────────────

    async def decide(self, query: str, mode: str = "auto") -> ExecutionPlan:
        """一次性完成全部决策 + 资源获取

        Args:
            query: 用户自然语言请求
            mode: 用户指定的模式（auto/direct/plan_and_execute/sub_agent）

        Returns:
            ExecutionPlan 包含模式、复杂度、prompt 前缀和已获取资源
        """
        # Step 1: 意图理解 + 复杂度评估 → 执行模式
        complexity = self._evaluate_complexity(query)
        execution_mode = self._resolve_mode(query, mode, complexity)

        # Step 2: 获取工具资源（一次性，缓存复用）
        resources = await self._resolve_resources()

        # Step 3: 装配执行计划
        plan = self._assemble_plan(execution_mode, complexity, resources)

        logger.info(
            f"[ReasoningEngine] 决策完成 | mode={execution_mode.value} "
            f"complexity={complexity.level.value}({complexity.score:.2f}) "
            f"query={query[:80]}"
        )
        return plan

    def invalidate_cache(self) -> None:
        """清除资源缓存（用于测试或资源变更后）"""
        self._resources_cache = None

    # ── 模式决策 ──────────────────────────────────────────

    def _resolve_mode(
        self,
        query: str,
        mode: str,
        complexity: ComplexityScore,
    ) -> ExecutionMode:
        """三级分类：显式指定 → 规则匹配 → 复杂度评估"""

        # Level 0: 用户显式指定
        if mode != "auto":
            try:
                resolved = ExecutionMode(mode)
                self._log_classify(query, mode, resolved, "explicit")
                return resolved
            except ValueError:
                logger.warning(f"无效的执行模式: {mode}，回退到 auto")

        # Level 1: 规则匹配（零延迟）
        if self._match_plan_patterns(query):
            # 进一步评估：HIGH/VERY_HIGH 升级为 SUB_AGENT
            if complexity.level in (ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH):
                self._log_classify(query, mode, ExecutionMode.SUB_AGENT, "rule+complexity")
                return ExecutionMode.SUB_AGENT
            self._log_classify(query, mode, ExecutionMode.PLAN_AND_EXECUTE, "rule")
            return ExecutionMode.PLAN_AND_EXECUTE

        if self._match_direct_patterns(query):
            self._log_classify(query, mode, ExecutionMode.DIRECT, "rule")
            return ExecutionMode.DIRECT

        # Level 2: 复杂度评估
        resolved = complexity.suggested_mode
        self._log_classify(query, mode, resolved, "complexity")
        return resolved

    # ── 复杂度评估 ────────────────────────────────────────

    def _evaluate_complexity(self, query: str) -> ComplexityScore:
        """五维度规则评估 + 模糊区间 LLM 兜底"""
        dimensions = {
            "task_count": self._estimate_task_count(query),
            "domain_span": self._estimate_domain_span(query),
            "dependency_depth": self._estimate_dependency_depth(query),
            "output_complexity": self._estimate_output_complexity(query),
            "reasoning_depth": self._estimate_reasoning_depth(query),
        }

        score = sum(dimensions[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        score = max(0.0, min(1.0, score))

        # TODO: 模糊区间 LLM 兜底（0.35~0.55）
        # if 0.35 <= score <= 0.55:
        #     score = await self._llm_classify(query, score)

        level = self._score_to_level(score)
        suggested_mode = _LEVEL_TO_MODE[level]

        return ComplexityScore(
            level=level,
            score=score,
            dimensions=dimensions,
            suggested_mode=suggested_mode,
        )

    def _estimate_task_count(self, query: str) -> float:
        """维度1: 估算隐含子任务数量（通过动词和连接词）"""
        # 中文动词
        zh_verbs = len(re.findall(
            r"(搜索|检索|查找|分析|对比|比较|生成|创建|编写|绘制|总结|翻译|执行|运行|部署)", query
        ))
        # 英文动词
        en_verbs = len(re.findall(
            r"\b(search|find|analyze|compare|generate|create|write|draw|summarize|translate|execute|run|deploy)\b",
            query,
            re.IGNORECASE,
        ))
        # 连接词
        connectors = len(re.findall(
            r"(然后|接着|之后|并且|同时|以及|再|最后|then|next|after|and|also|finally)",
            query,
            re.IGNORECASE,
        ))

        total = zh_verbs + en_verbs + connectors
        if total <= 1:
            return 0.1
        if total == 2:
            return 0.4
        if total == 3:
            return 0.6
        if total == 4:
            return 0.8
        return 1.0

    def _estimate_domain_span(self, query: str) -> float:
        """维度2: 检测跨领域关键词共现"""
        query_lower = query.lower()
        matched_domains = set()
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                matched_domains.add(domain)

        count = len(matched_domains)
        if count <= 1:
            return 0.1
        if count == 2:
            return 0.5
        if count == 3:
            return 0.8
        return 1.0

    def _estimate_dependency_depth(self, query: str) -> float:
        """维度3: 顺序连接词层级深度"""
        # 检测 "先...再...然后...最后" 的层级
        zh_seq = re.findall(r"(先|首先|再|然后|接着|之后|最后|最终)", query)
        en_seq = re.findall(
            r"\b(first|then|next|after\s?that|finally|lastly)\b",
            query,
            re.IGNORECASE,
        )
        depth = len(zh_seq) + len(en_seq)
        if depth <= 0:
            return 0.0
        if depth == 1:
            return 0.2
        if depth == 2:
            return 0.5
        if depth == 3:
            return 0.8
        return 1.0

    def _estimate_output_complexity(self, query: str) -> float:
        """维度4: 输出类型复杂度"""
        query_lower = query.lower()
        max_score = 0.1
        for keyword, score in _OUTPUT_KEYWORDS.items():
            if keyword.lower() in query_lower:
                max_score = max(max_score, score)
        return max_score

    def _estimate_reasoning_depth(self, query: str) -> float:
        """维度5: 推理类型深度"""
        query_lower = query.lower()
        max_score = 0.1
        for keyword, score in _REASONING_KEYWORDS.items():
            if keyword.lower() in query_lower:
                max_score = max(max_score, score)
        return max_score

    def _score_to_level(self, score: float) -> ComplexityLevel:
        """分数映射到复杂度等级"""
        if score < 0.25:
            return ComplexityLevel.LOW
        if score < 0.50:
            return ComplexityLevel.MEDIUM
        if score < 0.75:
            return ComplexityLevel.HIGH
        return ComplexityLevel.VERY_HIGH

    # ── 资源获取 ──────────────────────────────────────────

    async def _resolve_resources(self) -> ResolvedResources:
        """获取所有工具资源（MCP 连接只建立一次）"""
        if self._resources_cache is not None:
            return self._resources_cache

        # MCP toolsets（网络连接，最昂贵）
        mcp_toolsets = await self._get_mcp_toolsets()

        # Skill summary（内存读取）
        from src_deepagent.skills.registry import skill_registry

        skill_summary = skill_registry.get_skill_summary()

        # 桥接工具（基于 workers 创建）
        from src_deepagent.sub_agents.bridge import create_worker_tools

        bridge_tools = create_worker_tools(self._workers)

        # MCP 延迟加载工具名称（只注入名称到 prompt，不加载完整 schema）
        from src_deepagent.orchestrator.deferred_tools import deferred_tool_registry

        deferred_tool_names = deferred_tool_registry.get_tool_names()

        self._resources_cache = ResolvedResources(
            workers=self._workers,
            mcp_toolsets=mcp_toolsets,
            skill_summary=skill_summary,
            bridge_tools=bridge_tools,
            deferred_tool_names=deferred_tool_names,
        )

        logger.info(
            f"[ReasoningEngine] 资源获取完成 | "
            f"workers={len(self._workers)} "
            f"mcp={len(mcp_toolsets)} "
            f"bridge_tools={len(bridge_tools)} "
            f"deferred_tools={len(deferred_tool_names)}"
        )
        return self._resources_cache

    async def _get_mcp_toolsets(self) -> list[Any]:
        """获取 MCP toolsets（降级处理）"""
        # TODO: 接入 MCP 连接管理
        return []

    # ── 执行计划装配 ──────────────────��───────────────────

    def _assemble_plan(
        self,
        mode: ExecutionMode,
        complexity: ComplexityScore,
        resources: ResolvedResources,
    ) -> ExecutionPlan:
        """根据模式装配执行计划"""
        if mode == ExecutionMode.DIRECT:
            return ExecutionPlan(
                mode=mode,
                complexity=complexity,
                prompt_prefix="",
                resources=resources,
            )

        if mode == ExecutionMode.PLAN_AND_EXECUTE:
            return ExecutionPlan(
                mode=mode,
                complexity=complexity,
                prompt_prefix=_PLAN_EXECUTE_PREFIX,
                resources=resources,
            )

        if mode == ExecutionMode.SUB_AGENT:
            return ExecutionPlan(
                mode=mode,
                complexity=complexity,
                prompt_prefix=_SUB_AGENT_PREFIX,
                resources=resources,
            )

        # AUTO
        return ExecutionPlan(
            mode=mode,
            complexity=complexity,
            prompt_prefix="",
            resources=resources,
        )

    # ── 规则匹配 ──────────────────────────────────────────

    def _match_direct_patterns(self, query: str) -> bool:
        """匹配 direct 模式触发词"""
        for pattern in _DIRECT_PATTERNS_ZH:
            if pattern.search(query):
                return True
        for pattern in _DIRECT_PATTERNS_EN:
            if pattern.search(query):
                return True
        return False

    def _match_plan_patterns(self, query: str) -> bool:
        """匹配 plan_and_execute 模式触发词"""
        for pattern in _PLAN_PATTERNS_ZH:
            if pattern.search(query):
                return True
        for pattern in _PLAN_PATTERNS_EN:
            if pattern.search(query):
                return True
        return False

    # ── 日志 ──────────────────────────────────────────────

    def _log_classify(
        self,
        query: str,
        input_mode: str,
        resolved: ExecutionMode,
        match_level: str,
    ) -> None:
        truncated = query[:80] + "..." if len(query) > 80 else query
        logger.info(
            f"[ReasoningEngine] 分类 | query={truncated} "
            f"input_mode={input_mode} resolved={resolved.value} "
            f"level={match_level}"
        )
