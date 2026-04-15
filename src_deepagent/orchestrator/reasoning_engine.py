"""推理引擎 — ReasoningEngine

合并意图理解 + 复杂度评估 + 执行模式决策 + 工具资源获取。
两阶段流水线：Reason → Execute。
"""

from __future__ import annotations

import asyncio
import enum
import json
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
    ComplexityLevel.HIGH: ExecutionMode.PLAN_AND_EXECUTE,
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
class InfraResources:
    """底层基础设施资源（被桥接工具依赖）"""

    workers: dict[str, Any]


@dataclass(frozen=True)
class PromptContext:
    """注入 System Prompt 的文本内容"""

    skill_summary: str
    deferred_tool_summaries: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedResources:
    """一次获取的全部资源，整个请求生命周期内共享

    三层结构：
    - infra: 底层资源（Workers/MCP 连接），被 agent_tools 依赖
    - agent_tools: 给 LLM 的工具函数列表，基于 infra 构建
    - prompt_ctx: 给 System Prompt 的文本内容
    """

    infra: InfraResources
    agent_tools: list[Callable]
    prompt_ctx: PromptContext


@dataclass(frozen=True)
class ExecutionPlan:
    """推理引擎输出"""

    mode: ExecutionMode
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
        self._refresh_task: asyncio.Task | None = None

    async def startup(self) -> None:
        """启动时预热：建立 MCP 连接 + 预热资源缓存 + 启动定期刷新任务"""
        # 先建立 MCP 连接，工具元数据注册到 deferred_tool_registry
        await self._connect_mcp()
        # 再预热资源缓存
        await self._resolve_resources()

        from src_deepagent.config.settings import get_settings
        interval = get_settings().mcp.refresh_interval
        if interval > 0:
            self._refresh_task = asyncio.create_task(self._refresh_loop(interval))
            logger.info(f"[ReasoningEngine] MCP 定期刷新已启动 | interval={interval}s")

    async def shutdown(self) -> None:
        """关闭时取消刷新任务"""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("[ReasoningEngine] 刷新任务已停止")

    async def reload_mcp(self) -> int:
        """手动触发 MCP 工具刷新，清除资源缓存

        Returns:
            刷新后的工具总数
        """
        from src_deepagent.capabilities.mcp.client_manager import mcp_client_manager
        tool_count = await mcp_client_manager.refresh()
        self._resources_cache = None
        logger.info(f"[ReasoningEngine] MCP 手动刷新完成 | tools={tool_count}")
        return tool_count

    async def _refresh_loop(self, interval: int) -> None:
        """定期刷新 MCP 工具列表"""
        while True:
            await asyncio.sleep(interval)
            try:
                tool_count = await self.reload_mcp()
                logger.info(f"[ReasoningEngine] MCP 定期刷新完成 | tools={tool_count}")
            except Exception as e:
                logger.error(f"[ReasoningEngine] MCP 定期刷新失败 | error={e}")

    # ── 公开接口 ──────────────────────────────────────────

    async def decide(self, query: str, mode: str = "auto") -> ExecutionPlan:
        """一次性完成全部决策 + 资源获取

        Args:
            query: 用户自然语言请求
            mode: 用户指定的模式（auto/direct/plan_and_execute/sub_agent）

        Returns:
            ExecutionPlan 包含模式、prompt 前缀和已获取资源
        """
        # Step 1: 执行模式决策
        execution_mode = await self._resolve_mode(query, mode)

        # Step 2: 获取工具资源（一次性，缓存复用）
        resources = await self._resolve_resources()

        # Step 3: 装配执行计划
        plan = self._assemble_plan(execution_mode, resources)

        logger.info(
            f"[ReasoningEngine] 决策完成 | mode={execution_mode.value} "
            f"query={query[:80]}"
        )
        return plan

    def invalidate_cache(self) -> None:
        """清除资源缓存（用于测试或资源变更后）"""
        self._resources_cache = None

    # ── 模式决策 ──────────────────────────────────────────

    async def _resolve_mode(
        self,
        query: str,
        mode: str,
    ) -> ExecutionMode:
        """模式决策：显式指定 → 快筛 → LLM 主决策 → 规则降级"""

        # Level 0: 用户显式指定
        if mode != "auto":
            try:
                resolved = ExecutionMode(mode)
                self._log_classify(query, mode, resolved, "explicit")
                return resolved
            except ValueError:
                logger.warning(f"无效的执行模式: {mode}，回退到 auto")

        # Level 1: 高置信度快筛（极短无动词 → DIRECT，省一次 LLM 调用）
        if self._is_trivial_query(query):
            self._log_classify(query, mode, ExecutionMode.DIRECT, "trivial_fast")
            return ExecutionMode.DIRECT

        # Level 2: LLM 主分类
        llm_mode = await self._llm_classify_primary(query)
        if llm_mode is not None:
            self._log_classify(query, mode, llm_mode, "llm_primary")
            return llm_mode

        # Level 3: LLM 失败 → 降级到规则+复杂度评估（此时才计算）
        logger.info("[ReasoningEngine] LLM 主分类失败，降级到规则评估")
        complexity = await self._evaluate_complexity(query)

        if self._match_plan_patterns(query):
            if complexity.level in (ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH):
                self._log_classify(query, mode, ExecutionMode.SUB_AGENT, "rule+complexity")
                return ExecutionMode.SUB_AGENT
            self._log_classify(query, mode, ExecutionMode.PLAN_AND_EXECUTE, "rule")
            return ExecutionMode.PLAN_AND_EXECUTE

        if self._match_direct_patterns(query):
            self._log_classify(query, mode, ExecutionMode.DIRECT, "rule")
            return ExecutionMode.DIRECT

        resolved = complexity.suggested_mode
        self._log_classify(query, mode, resolved, "complexity")
        return resolved

    def _is_trivial_query(self, query: str) -> bool:
        """高置信度快筛：极短查询且无任务动词 → 一定是 DIRECT"""
        if len(query) > 30:
            return False
        # 无任何任务动词
        has_zh_verb = bool(re.search(
            r"(搜索|检索|查找|分析|对比|比较|生成|创建|编写|绘制|总结|翻译|执行|运行|部署)", query
        ))
        has_en_verb = bool(re.search(
            r"\b(search|find|analyze|compare|generate|create|write|draw|summarize|translate|execute|run|deploy)\b",
            query,
            re.IGNORECASE,
        ))
        return not has_zh_verb and not has_en_verb

    # ── 复杂度评估 ────────────────────────────────────────

    async def _evaluate_complexity(self, query: str) -> ComplexityScore:
        """五维度规则评估（仅作为 LLM 失败时的降级兜底）"""
        dimensions = {
            "task_count": self._estimate_task_count(query),
            "domain_span": self._estimate_domain_span(query),
            "dependency_depth": self._estimate_dependency_depth(query),
            "output_complexity": self._estimate_output_complexity(query),
            "reasoning_depth": self._estimate_reasoning_depth(query),
        }

        score = sum(dimensions[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        score = max(0.0, min(1.0, score))

        level = self._score_to_level(score)
        suggested_mode = _LEVEL_TO_MODE[level]

        return ComplexityScore(
            level=level,
            score=score,
            dimensions=dimensions,
            suggested_mode=suggested_mode,
        )

    def _estimate_task_count(self, query: str) -> float:
        """维度1: 估算隐含子任务数量（仅通过动词，连接词由 dependency_depth 负责）"""
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

        total = zh_verbs + en_verbs
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
            return 0.3
        if count == 3:
            return 0.7
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

    async def _llm_classify_primary(self, query: str) -> ExecutionMode | None:
        """LLM 主决策分类

        直接返回执行模式，而非分数。超时或异常时返回 None（降级到规则评估）。
        """
        from src_deepagent.config.settings import get_settings
        from src_deepagent.llm.config import get_model

        settings = get_settings()
        timeout = settings.reasoning.llm_classify_timeout

        prompt = (
            "你是一个 AI Agent 任务路由器。根据用户查询判断应使用哪种执行模式。\n\n"
            "可选模式（只能选一个）：\n"
            "- direct: 简单任务，可直接回答或单次工具调用（问候、翻译、单步查询、简单问答）\n"
            "- auto: 中等任务，需要 LLM 自主判断调用哪些工具，但不需要显式规划（单领域多步骤）\n"
            "- plan_and_execute: 复杂多步骤任务，需要先规划 DAG 再按序执行（跨领域、有依赖链）\n"
            "- sub_agent: 非常复杂的任务，需要多个专业角色协作完成（研究+分析+报告等）\n\n"
            "判断要点：\n"
            "- 注意区分「描述性提及」和「实际任务动词」，如「搜索功能有 bug」中的搜索不是任务\n"
            "- 否定语境中的动词不算任务，如「不要搜索，直接告诉我」应为 direct\n"
            "- 同义动词只算一个任务，如「搜索并检索」是一个动作\n"
            "- 关注实际要完成的独立步骤数量，而非关键词数量\n\n"
            "示例：\n"
            '- "你好" → {"mode": "direct", "reason": "简单问候"}\n'
            '- "翻译这段话" → {"mode": "direct", "reason": "单步翻译任务"}\n'
            '- "不要搜索，直接告诉我答案" → {"mode": "direct", "reason": "否定语境，实际是直接问答"}\n'
            '- "搜索功能的分析模块有 bug" → {"mode": "direct", "reason": "描述性提及，不是多步骤任务"}\n'
            '- "写一个快速排序算法" → {"mode": "auto", "reason": "单领域编码任务，需要工具但不需要规划"}\n'
            '- "搜索并检索相关论文" → {"mode": "auto", "reason": "同义动词，实际是单步搜索"}\n'
            '- "写一个分布式爬虫系统，支持多节点调度、断点续传" → {"mode": "auto", "reason": "单领域复杂编码，LLM 自主判断即可"}\n'
            '- "先搜索最新论文，再对比分析趋势，最后生成报告" → {"mode": "plan_and_execute", "reason": "三个有依赖的步骤，需要规划"}\n'
            '- "检索专利数据，分析技术趋势，生成可视化图表，并撰写分析报告" → {"mode": "sub_agent", "reason": "跨多领域，需要研究+分析+可视化+写作协作"}\n\n'
            f"用户查询：{query[:500]}\n\n"
            '请只返回 JSON：{"mode": "direct|auto|plan_and_execute|sub_agent", "reason": "一句话理由"}'
        )

        try:
            from pydantic_ai import Agent
            from pydantic_ai.settings import ModelSettings

            classifier = Agent(
                model=get_model("classifier"),
                output_type=str,
                instructions="你是任务路由器，只返回 JSON，不要其他内容。",
                name="ModeClassifier",
            )

            result = await asyncio.wait_for(
                classifier.run(
                    prompt,
                    model_settings=ModelSettings(temperature=0.0),
                ),
                timeout=timeout,
            )

            raw = result.output if hasattr(result, "output") else str(result)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            parsed = json.loads(raw)
            mode_str = parsed["mode"].strip().lower()
            reason = parsed.get("reason", "")

            try:
                llm_mode = ExecutionMode(mode_str)
            except ValueError:
                logger.warning(
                    f"[ReasoningEngine] LLM 返回无效模式: {mode_str}"
                )
                return None

            logger.info(
                f"[ReasoningEngine] LLM 主分类完成 | "
                f"mode={llm_mode.value} reason={reason}"
            )
            return llm_mode

        except asyncio.TimeoutError:
            logger.warning(
                f"[ReasoningEngine] LLM 主分类超时({timeout}s)，降级到规则评估"
            )
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"[ReasoningEngine] LLM 主分类解析失败 | error={e}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"[ReasoningEngine] LLM 主分类异常 | error={e}"
            )
            return None

    # ── 资源获取 ──────────────────────────────────────────

    async def _resolve_resources(self) -> ResolvedResources:
        """获取工具资源（缓存复用，MCP 刷新后自动失效重建）"""
        if self._resources_cache is not None:
            return self._resources_cache

        # Skill summary（内存读取）
        from src_deepagent.capabilities.skills.registry import skill_registry

        skill_summary = skill_registry.get_skill_summary()

        # 桥接工具（基于 workers 创建）
        from src_deepagent.capabilities.base_tools import create_base_tools

        agent_tools = create_base_tools(self._workers)

        # MCP 延迟加载工具摘要（名称+描述注入 prompt，让 LLM 知道工具用途）
        from src_deepagent.capabilities.mcp.deferred_registry import deferred_tool_registry

        deferred_tool_summaries = deferred_tool_registry.get_tool_summaries()

        infra = InfraResources(workers=self._workers)

        prompt_ctx = PromptContext(
            skill_summary=skill_summary,
            deferred_tool_summaries=deferred_tool_summaries,
        )

        self._resources_cache = ResolvedResources(
            infra=infra,
            agent_tools=agent_tools,
            prompt_ctx=prompt_ctx,
        )

        logger.info(
            f"[ReasoningEngine] 资源获取完成 | "
            f"workers={len(self._workers)} "
            f"agent_tools={len(agent_tools)} "
            f"deferred_tools={len(deferred_tool_summaries)}"
        )
        return self._resources_cache

    async def _connect_mcp(self) -> None:
        """建立 MCP 连接，工具元数据注册到 deferred_tool_registry"""
        from src_deepagent.config.settings import get_settings
        from src_deepagent.capabilities.mcp.client_manager import (
            mcp_client_manager,
            parse_mcp_servers,
        )

        settings = get_settings()
        endpoints = parse_mcp_servers(
            servers_json=settings.mcp.servers_json,
            fallback_url=settings.mcp.server_url,
        )

        if not endpoints:
            return

        try:
            tool_count = await mcp_client_manager.connect(endpoints)
            logger.info(f"[ReasoningEngine] MCP 连接完成 | tools={tool_count}")
        except Exception as e:
            logger.error(f"[ReasoningEngine] MCP 连接异常 | error={e}")

    # ── 执行计划装配 ──────────────────��───────────────────

    def _assemble_plan(
        self,
        mode: ExecutionMode,
        resources: ResolvedResources,
    ) -> ExecutionPlan:
        """根据模式装配执行计划"""
        prefix_map = {
            ExecutionMode.PLAN_AND_EXECUTE: _PLAN_EXECUTE_PREFIX,
            ExecutionMode.SUB_AGENT: _SUB_AGENT_PREFIX,
        }
        return ExecutionPlan(
            mode=mode,
            prompt_prefix=prefix_map.get(mode, ""),
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
