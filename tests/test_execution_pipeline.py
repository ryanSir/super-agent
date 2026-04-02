"""测试三阶段执行管道端到端流程"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestrator.intent_router import ExecutionMode, IntentRouter
from src.orchestrator.toolset_assembler import AssembleResult, ToolSetAssembler


class TestThreeStagePipeline:
    """验证 Classify → Assemble → Execute 三阶段管道"""

    def test_direct_query_classified_correctly(self):
        """简单代码任务被分类为 DIRECT"""
        router = IntentRouter()
        mode = router.classify("用 Python 写一个快速排序算法", mode="auto")
        assert mode == ExecutionMode.DIRECT

    def test_direct_mode_filters_plan_tool(self):
        """DIRECT 模式过滤 plan_and_decompose"""
        assembler = ToolSetAssembler()
        result = assembler.assemble(ExecutionMode.DIRECT)
        assert "plan_and_decompose" in result.tool_filter

    def test_plan_query_classified_correctly(self):
        """多步骤任务被分类为 PLAN_AND_EXECUTE"""
        router = IntentRouter()
        mode = router.classify("先检索专利数据，再分析趋势，最后生成报告", mode="auto")
        assert mode == ExecutionMode.PLAN_AND_EXECUTE

    def test_plan_mode_injects_prefix(self):
        """PLAN_AND_EXECUTE 模式注入 prompt prefix"""
        assembler = ToolSetAssembler()
        result = assembler.assemble(ExecutionMode.PLAN_AND_EXECUTE)
        assert "plan_and_decompose" in result.prompt_prefix

    def test_auto_mode_no_constraints(self):
        """AUTO 模式无约束"""
        router = IntentRouter()
        mode = router.classify("帮我看看这个数据", mode="auto")
        assert mode == ExecutionMode.AUTO

        assembler = ToolSetAssembler()
        result = assembler.assemble(ExecutionMode.AUTO)
        assert result.tool_filter is None
        assert result.prompt_prefix == ""

    def test_end_to_end_direct_flow(self):
        """端到端：写快排 → DIRECT → 过滤规划工具"""
        router = IntentRouter()
        assembler = ToolSetAssembler()

        # Stage 1: Classify
        mode = router.classify("用 Python 写一个快速排序并测试性能", mode="auto")
        assert mode == ExecutionMode.DIRECT

        # Stage 2: Assemble
        result = assembler.assemble(mode)
        assert "plan_and_decompose" in result.tool_filter
        assert result.prompt_prefix == ""

    def test_end_to_end_plan_flow(self):
        """端到端：检索+分析+可视化 → PLAN_AND_EXECUTE → 注入 prefix"""
        router = IntentRouter()
        assembler = ToolSetAssembler()

        # Stage 1: Classify
        mode = router.classify("检索 AI 专利，分析趋势变化，用图表展示", mode="auto")
        assert mode == ExecutionMode.PLAN_AND_EXECUTE

        # Stage 2: Assemble
        result = assembler.assemble(mode)
        assert result.tool_filter is None
        assert "plan_and_decompose" in result.prompt_prefix

    def test_explicit_mode_bypasses_classification(self):
        """显式指定 mode 跳过规则匹配"""
        router = IntentRouter()
        assembler = ToolSetAssembler()

        # 即使 query 看起来像 direct，显式指定 plan_and_execute
        mode = router.classify("写个快排", mode="plan_and_execute")
        assert mode == ExecutionMode.PLAN_AND_EXECUTE

        result = assembler.assemble(mode)
        assert "plan_and_decompose" in result.prompt_prefix
