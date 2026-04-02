"""意图路由器

规则优先 + LLM fallback，将用户请求分类为 direct/auto/plan_and_execute 模式。
"""

from __future__ import annotations

import enum
import re
from typing import Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionMode(str, enum.Enum):
    """执行模式"""
    DIRECT = "direct"
    AUTO = "auto"
    PLAN_AND_EXECUTE = "plan_and_execute"


# 中文 direct 触发模式：单一动作 + 明确对象
_DIRECT_PATTERNS_ZH = [
    re.compile(r"(写|实现|编写|生成|创建|开发).{0,10}(代码|算法|脚本|程序|函数|类|模块|工具|爬虫|排序|服务)"),
    re.compile(r"(搜索|检索|查找|查询|搜一下|找).{0,10}(论文|专利|文献|文档|资料|数据)"),
    re.compile(r"(翻译|总结|解释|概括|摘要|改写|润色)"),
    re.compile(r"(画|绘制|生成).{0,6}(图表|图|表格|PPT|幻灯片)"),
]

# 英文 direct 触发模式
_DIRECT_PATTERNS_EN = [
    re.compile(r"(write|implement|create|build|develop|code|generate)\s.{0,20}(script|code|function|class|algorithm|program|tool|sorter|crawler|service)", re.IGNORECASE),
    re.compile(r"(search|find|look\s?up|query|retrieve)\s.{0,20}(paper|patent|document|article|literature)", re.IGNORECASE),
    re.compile(r"(translate|summarize|explain|paraphrase|rewrite)", re.IGNORECASE),
]

# plan_and_execute 触发模式：多步骤连接词
_PLAN_PATTERNS_ZH = [
    re.compile(r"(先|首先).{2,30}(再|然后|接着|之后).{2,30}(最后|最终|并且)?"),
    re.compile(r".{2,20}(并且|同时|以及).{2,20}(并且|同时|以及|然后|再)"),
    re.compile(r"(检索|搜索|查询).{2,20}(分析|对比|比较).{0,20}(生成|展示|可视化|输出|报告)?"),
    re.compile(r"(对比|比较|分析).{2,20}(趋势|变化|差异).{0,20}(图表|可视化|报告)?"),
]

_PLAN_PATTERNS_EN = [
    re.compile(r"(first|start\sby).{5,40}(then|next|after\sthat).{5,40}(finally|lastly)?", re.IGNORECASE),
    re.compile(r"(search|retrieve|fetch).{5,30}(analyze|compare).{0,30}(generate|visualize|report)?", re.IGNORECASE),
]


class IntentRouter:
    """意图路由器

    两级分类策略：
    - Level 0: 用户显式指定 mode → 直通
    - Level 1: 规则匹配（零延迟）
    - Level 2: 默认 auto（Agent 自主决定）
    """

    def classify(self, query: str, mode: str = "auto") -> ExecutionMode:
        """分类用户请求的执行模式

        Args:
            query: 用户自然语言请求
            mode: 用户指定的模式（auto/direct/plan_and_execute）

        Returns:
            ExecutionMode 枚举值
        """
        # Level 0: 用户显式指定
        if mode != "auto":
            resolved = ExecutionMode(mode)
            self._log(query, mode, resolved, "explicit")
            return resolved

        # Level 1: 规则匹配
        if self._match_plan_patterns(query):
            self._log(query, mode, ExecutionMode.PLAN_AND_EXECUTE, "rule")
            return ExecutionMode.PLAN_AND_EXECUTE

        if self._match_direct_patterns(query):
            self._log(query, mode, ExecutionMode.DIRECT, "rule")
            return ExecutionMode.DIRECT

        # Level 2: 默认 auto
        self._log(query, mode, ExecutionMode.AUTO, "default")
        return ExecutionMode.AUTO

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

    def _log(
        self,
        query: str,
        input_mode: str,
        resolved: ExecutionMode,
        match_level: str,
    ) -> None:
        """记录分类结果"""
        truncated = query[:100] + "..." if len(query) > 100 else query
        logger.info(
            f"[IntentRouter] 分类完成 | "
            f"query={truncated} input_mode={input_mode} "
            f"resolved_mode={resolved.value} match_level={match_level}"
        )


# 全局单例
intent_router = IntentRouter()
