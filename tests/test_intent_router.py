"""测试 IntentRouter"""

import pytest

from src.orchestrator.intent_router import ExecutionMode, IntentRouter


@pytest.fixture
def router():
    return IntentRouter()


class TestExplicitMode:
    """Level 0: 用户显式指定 mode"""

    def test_explicit_direct(self, router):
        result = router.classify("任意内容", mode="direct")
        assert result == ExecutionMode.DIRECT

    def test_explicit_plan(self, router):
        result = router.classify("任意内容", mode="plan_and_execute")
        assert result == ExecutionMode.PLAN_AND_EXECUTE

    def test_explicit_auto_triggers_rules(self, router):
        """auto 模式不直通，走规则匹配"""
        result = router.classify("写个快排算法", mode="auto")
        # 应该被规则匹配为 DIRECT，而非直通 AUTO
        assert result == ExecutionMode.DIRECT


class TestDirectPatternsChinese:
    """Level 1: 中文 direct 规则匹配"""

    def test_write_code(self, router):
        assert router.classify("用 Python 写一个快速排序算法") == ExecutionMode.DIRECT

    def test_implement_function(self, router):
        assert router.classify("实现一个二叉树遍历函数") == ExecutionMode.DIRECT

    def test_generate_script(self, router):
        assert router.classify("生成一个数据清洗脚本") == ExecutionMode.DIRECT

    def test_search_paper(self, router):
        assert router.classify("搜索 AI 相关论文") == ExecutionMode.DIRECT

    def test_find_patent(self, router):
        assert router.classify("查找近三年的专利数据") == ExecutionMode.DIRECT

    def test_translate(self, router):
        assert router.classify("翻译这段英文") == ExecutionMode.DIRECT

    def test_summarize(self, router):
        assert router.classify("总结这篇文章的要点") == ExecutionMode.DIRECT

    def test_create_tool(self, router):
        assert router.classify("编写一个爬虫工具") == ExecutionMode.DIRECT


class TestDirectPatternsEnglish:
    """Level 1: 英文 direct 规则匹配"""

    def test_write_script(self, router):
        assert router.classify("Write a Python script to sort numbers") == ExecutionMode.DIRECT

    def test_implement_algorithm(self, router):
        assert router.classify("Implement a binary search algorithm") == ExecutionMode.DIRECT

    def test_create_function(self, router):
        assert router.classify("Create a function to parse JSON") == ExecutionMode.DIRECT

    def test_search_papers(self, router):
        assert router.classify("Search for machine learning papers") == ExecutionMode.DIRECT

    def test_summarize_text(self, router):
        assert router.classify("Summarize this article") == ExecutionMode.DIRECT


class TestPlanPatternsChinese:
    """Level 1: 中文 plan_and_execute 规则匹配"""

    def test_multi_step_with_connectors(self, router):
        assert router.classify("先检索专利数据，再分析趋势，最后生成报告") == ExecutionMode.PLAN_AND_EXECUTE

    def test_search_analyze_visualize(self, router):
        assert router.classify("检索近三个月的 AI 专利，分析趋势，并用图表展示") == ExecutionMode.PLAN_AND_EXECUTE

    def test_compare_and_analyze(self, router):
        assert router.classify("对比数据库中的专利数据，分析趋势变化") == ExecutionMode.PLAN_AND_EXECUTE


class TestPlanPatternsEnglish:
    """Level 1: 英文 plan_and_execute 规则匹配"""

    def test_first_then_finally(self, router):
        assert router.classify("First search for patents, then analyze trends, finally generate a report") == ExecutionMode.PLAN_AND_EXECUTE

    def test_search_and_analyze(self, router):
        assert router.classify("Search for AI papers and analyze their citation trends and visualize results") == ExecutionMode.PLAN_AND_EXECUTE


class TestDefaultAuto:
    """Level 2: 模糊意图返回 auto"""

    def test_ambiguous_question(self, router):
        assert router.classify("帮我看看这个数据有什么问题") == ExecutionMode.AUTO

    def test_general_chat(self, router):
        assert router.classify("你好，今天天气怎么样") == ExecutionMode.AUTO

    def test_vague_request(self, router):
        assert router.classify("优化一下性能") == ExecutionMode.AUTO


class TestPlanPriorityOverDirect:
    """plan 模式优先于 direct（多步骤任务中可能包含 direct 触发词）"""

    def test_search_then_write(self, router):
        """包含"搜索"（direct 触发词）但也有多步骤连接词"""
        result = router.classify("先搜索相关论文，再写一份综述报告")
        assert result == ExecutionMode.PLAN_AND_EXECUTE
