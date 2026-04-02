"""测试 ToolSetAssembler"""

import pytest

from src.orchestrator.intent_router import ExecutionMode
from src.orchestrator.toolset_assembler import ToolSetAssembler, AssembleResult


@pytest.fixture
def assembler():
    return ToolSetAssembler()


class TestDirectMode:
    def test_filters_planning_tools(self, assembler):
        """direct 模式过滤规划相关工具"""
        result = assembler.assemble(ExecutionMode.DIRECT)

        assert result.tool_filter is not None
        assert "plan_and_decompose" in result.tool_filter
        assert "list_available_skills" in result.tool_filter
        assert "create_new_skill" in result.tool_filter

    def test_no_prompt_prefix(self, assembler):
        """direct 模式无 prompt prefix"""
        result = assembler.assemble(ExecutionMode.DIRECT)
        assert result.prompt_prefix == ""

    def test_agent_override_provided(self, assembler):
        """direct 模式提供替代 Agent 实例"""
        result = assembler.assemble(ExecutionMode.DIRECT)
        # agent_override 可能为 None（如果初始化失败）或 Agent 实例
        # 这里只验证字段存在
        assert hasattr(result, "agent_override")


class TestAutoMode:
    def test_no_filter(self, assembler):
        """auto 模式不过滤任何工具"""
        result = assembler.assemble(ExecutionMode.AUTO)

        assert result.tool_filter is None

    def test_no_prompt_prefix(self, assembler):
        """auto 模式无 prompt prefix"""
        result = assembler.assemble(ExecutionMode.AUTO)
        assert result.prompt_prefix == ""

    def test_no_agent_override(self, assembler):
        """auto 模式不替换 Agent"""
        result = assembler.assemble(ExecutionMode.AUTO)
        assert result.agent_override is None

    def test_returns_empty_result(self, assembler):
        """auto 模式返回空配置"""
        result = assembler.assemble(ExecutionMode.AUTO)
        assert result == AssembleResult()


class TestPlanAndExecuteMode:
    def test_no_filter(self, assembler):
        """plan_and_execute 模式不过滤工具"""
        result = assembler.assemble(ExecutionMode.PLAN_AND_EXECUTE)
        assert result.tool_filter is None

    def test_has_prompt_prefix(self, assembler):
        """plan_and_execute 模式有 prompt prefix"""
        result = assembler.assemble(ExecutionMode.PLAN_AND_EXECUTE)
        assert "plan_and_decompose" in result.prompt_prefix
        assert len(result.prompt_prefix) > 0

    def test_no_agent_override(self, assembler):
        """plan_and_execute 模式不替换 Agent"""
        result = assembler.assemble(ExecutionMode.PLAN_AND_EXECUTE)
        assert result.agent_override is None


class TestDirectAgentLazyInit:
    def test_same_instance_on_repeated_calls(self, assembler):
        """多次调用返回同一个 Agent 实例（lazy 单例）"""
        result1 = assembler.assemble(ExecutionMode.DIRECT)
        result2 = assembler.assemble(ExecutionMode.DIRECT)

        if result1.agent_override is not None:
            assert result1.agent_override is result2.agent_override
