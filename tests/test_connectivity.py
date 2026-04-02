"""连通性测试 - 验证各 Skill、API Worker 和沙箱环境是否可用

运行全部测试：
    pytest tests/test_connectivity.py -v -s

单独测试某项：
    pytest tests/test_connectivity.py::TestSkillConnectivity::test_paper_search -v -s
    pytest tests/test_connectivity.py::TestSandboxConnectivity::test_sandbox_basic -v -s
    pytest tests/test_connectivity.py::TestAPIWorkerConnectivity::test_api_worker_http -v -s
"""

import os
import pytest

pytestmark = pytest.mark.asyncio


# ============================================================
# Skill 连通性测试
# ============================================================

class TestSkillConnectivity:
    """测试各 Skill 脚本是否可执行"""

    async def test_paper_search(self):
        """paper-search: 论文语义搜索（需要内网 validation_rag API）"""
        from src.skills.executor import run_script

        result = await run_script(
            skill_name="paper-search",
            script_name="paper_search.py",
            args=["lithium battery", "--doc-num", "1"],
            timeout=30,
        )
        _print_result("paper-search", result)
        assert result.exit_code != -1, f"脚本无法启动: {result.stderr}"
        assert result.success, f"执行失败 (exit={result.exit_code}): {result.stderr[:300]}"

    async def test_baidu_search(self):
        """baidu-search: 百度 AI 搜索（需要 BAIDU_API_KEY）"""
        if not os.environ.get("BAIDU_API_KEY"):
            pytest.skip("BAIDU_API_KEY 未配置")

        from src.skills.executor import run_script

        result = await run_script(
            skill_name="baidu-search",
            script_name="search.py",
            args=['{"query": "苏州天气", "count": 1}'],
            timeout=30,
        )
        _print_result("baidu-search", result)
        assert result.exit_code != -1, f"脚本无法启动: {result.stderr}"
        assert result.success, f"执行失败 (exit={result.exit_code}): {result.stderr[:300]}"

    async def test_baidu_search_executor(self):
        """baidu-search-executor: 百度搜索执行器变体"""
        if not os.environ.get("BAIDU_API_KEY"):
            pytest.skip("BAIDU_API_KEY 未配置")

        from src.skills.executor import run_script

        result = await run_script(
            skill_name="baidu-search-executor",
            script_name="execute.py",
            args=['{"query": "苏州天气", "count": 1}'],
            timeout=30,
        )
        _print_result("baidu-search-executor", result)
        assert result.exit_code != -1, f"脚本无法启动: {result.stderr}"
        assert result.success, f"执行失败 (exit={result.exit_code}): {result.stderr[:300]}"

    async def test_direct_baidu_search(self):
        """direct-baidu-search: 直接百度搜索"""
        if not os.environ.get("BAIDU_API_KEY"):
            pytest.skip("BAIDU_API_KEY 未配置")

        from src.skills.executor import run_script

        result = await run_script(
            skill_name="direct-baidu-search",
            script_name="direct_search.py",
            args=['{"query": "苏州天气", "count": 1}'],
            timeout=30,
        )
        _print_result("direct-baidu-search", result)
        assert result.exit_code != -1, f"脚本无法启动: {result.stderr}"
        assert result.success, f"执行失败 (exit={result.exit_code}): {result.stderr[:300]}"

    async def test_exec_baidu_search(self):
        """exec-baidu-search: exec 版百度搜索"""
        if not os.environ.get("BAIDU_API_KEY"):
            pytest.skip("BAIDU_API_KEY 未配置")

        from src.skills.executor import run_script

        result = await run_script(
            skill_name="exec-baidu-search",
            script_name="exec_search.py",
            args=['{"query": "苏州天气", "count": 1}'],
            timeout=30,
        )
        _print_result("exec-baidu-search", result)
        assert result.exit_code != -1, f"脚本无法启动: {result.stderr}"
        assert result.success, f"执行失败 (exit={result.exit_code}): {result.stderr[:300]}"

    async def test_ai_ppt_generator(self):
        """ai-ppt-generator: PPT 生成（需要百度 AI PPT API Key）"""
        if not os.environ.get("BAIDU_API_KEY"):
            pytest.skip("BAIDU_API_KEY 未配置")

        from src.skills.executor import run_script

        result = await run_script(
            skill_name="ai-ppt-generator",
            script_name="generate_ppt.py",
            args=["--help"],
            timeout=15,
        )
        _print_result("ai-ppt-generator", result)
        # --help 通常 exit_code=0 或 1，只要脚本能启动就算通
        assert result.exit_code != -1, f"脚本无法启动: {result.stderr}"

    async def test_skill_registry(self):
        """验证所有 Skill 均已正确注册"""
        from src.skills.registry import skill_registry

        skills = skill_registry.list_skills()
        names = [s.metadata.name for s in skills]
        print(f"\n已注册 Skill ({len(names)}): {names}")
        assert len(skills) > 0, "没有任何 Skill 被注册"


# ============================================================
# API Worker 连通性测试
# ============================================================

class TestAPIWorkerConnectivity:
    """测试 APICallWorker 是否能发出 HTTP 请求"""

    async def test_api_worker_http(self):
        """APICallWorker: 发起一个简单 HTTP GET 请求"""
        from src.workers.native.api_call_worker import APICallWorker
        from src.schemas.agent import TaskNode, TaskType

        worker = APICallWorker()
        task = TaskNode(
            task_id="conn-test-api",
            task_type=TaskType.API_CALL,
            description="连通性测试",
            input_data={
                "url": "https://httpbin.org/get",
                "method": "GET",
            },
        )
        result = await worker.execute(task)
        _print_worker_result("APICallWorker → httpbin.org", result)
        assert result.success, f"HTTP 请求失败: {result.error}"

    async def test_api_worker_internal(self):
        """APICallWorker: 访问内网 Eureka 服务（需要内网环境）"""
        from src.workers.native.api_call_worker import APICallWorker
        from src.schemas.agent import TaskNode, TaskType

        worker = APICallWorker()
        task = TaskNode(
            task_id="conn-test-internal",
            task_type=TaskType.API_CALL,
            description="内网连通性测试",
            input_data={
                "url": "http://qa-s-core-eureka.patsnap.info/eureka/",
                "method": "GET",
            },
        )
        result = await worker.execute(task)
        _print_worker_result("APICallWorker → 内网 Eureka", result)
        # 403 = 网络可达但需要认证，视为连通
        if not result.success and result.error and "403" in result.error:
            print("  [内网] 网络可达，但需要认证 (HTTP 403) ✓")
            return
        assert result.success, f"内网 API 不可达: {result.error}"


# ============================================================
# RAG Worker 连通性测试
# ============================================================

class TestRAGWorkerConnectivity:
    """测试 RAGWorker 是否能连接 Milvus"""

    async def test_milvus_connection(self):
        """RAGWorker: 连接 Milvus 向量数据库"""
        from src.workers.native.rag_worker import RAGWorker
        from src.schemas.agent import TaskNode, TaskType

        worker = RAGWorker()
        task = TaskNode(
            task_id="conn-test-rag",
            task_type=TaskType.RAG_RETRIEVAL,
            description="Milvus 连通性测试",
            input_data={"query": "test", "top_k": 1},
        )
        result = await worker.execute(task)
        _print_worker_result("RAGWorker → Milvus", result)
        assert result.success, f"Milvus 连接失败: {result.error}"


# ============================================================
# 沙箱连通性测试
# ============================================================

class TestSandboxConnectivity:
    """测试 E2B 沙箱环境是否可用"""

    async def test_sandbox_import(self):
        """检查 e2b 包是否已安装"""
        try:
            import e2b  # noqa: F401
            print("\n[sandbox] e2b 包已安装 ✓")
        except ImportError as e:
            pytest.fail(f"e2b 包未安装: {e}\n请运行: pip install e2b")

    async def test_sandbox_api_key(self):
        """检查 E2B_API_KEY 是否已配置"""
        from src.config.settings import get_settings
        settings = get_settings()
        api_key = settings.e2b.e2b_api_key
        print(f"\n[sandbox] E2B_API_KEY: {'已配置' if api_key else '未配置'}")
        assert api_key, "E2B_API_KEY 未配置，请在 .env 中设置"

    async def test_sandbox_pi_agent(self):
        """SandboxWorker: 检查 pi 命令是否在本地可用"""
        from src.workers.sandbox.sandbox_manager import SandboxManager
        from src.schemas.sandbox import SandboxTask

        manager = SandboxManager()
        task = SandboxTask(
            task_id="conn-test-pi-agent",
            instruction="check pi",
            context_files={},
            timeout=60,
        )

        sandbox_id = ""
        try:
            sandbox_id = await manager.create_sandbox(task)
            result = await manager.execute_command(
                sandbox_id,
                "which pi 2>&1 || echo 'pi NOT FOUND'",
                timeout=10,
            )
            stdout = result.get("stdout", "").strip()
            print(f"\n[sandbox] pi 路径: {stdout}")
            assert "NOT FOUND" not in stdout, (
                "pi 命令不存在！请运行: npm install -g @mariozechner/pi-coding-agent"
            )
            print("[sandbox] pi 可用 ✓")
        finally:
            if sandbox_id:
                await manager.destroy_sandbox(sandbox_id)

    async def test_sandbox_basic(self):
        """SandboxWorker: 创建沙箱并执行 echo 命令"""
        from src.workers.sandbox.sandbox_manager import SandboxManager
        from src.schemas.sandbox import SandboxTask

        manager = SandboxManager()
        task = SandboxTask(
            task_id="conn-test-sandbox",
            instruction="echo hello",
            context_files={},
            timeout=60,
        )

        sandbox_id = ""
        try:
            sandbox_id = await manager.create_sandbox(task)
            print(f"\n[sandbox] 沙箱创建成功 | sandbox_id={sandbox_id}")

            result = await manager.execute_command(sandbox_id, "echo hello", timeout=10)
            print(f"[sandbox] 命令执行结果: {result}")
            assert result.get("exit_code") == 0, f"命令执行失败: {result}"
            print("[sandbox] 沙箱连通性测试通过 ✓")
        except Exception as e:
            err = str(e)
            if "invalid username" in err or "unauthenticated" in err:
                pytest.fail(
                    f"沙箱命令执行认证失败: {err}\n"
                    "可能原因: e2b SDK 版本与沙箱环境不兼容，"
                    "请检查 e2b 包版本或沙箱模板配置"
                )
            raise
        finally:
            if sandbox_id:
                await manager.destroy_sandbox(sandbox_id)
                print(f"[sandbox] 沙箱已销毁 | sandbox_id={sandbox_id}")


# ============================================================
# MCP 连通性测试
# ============================================================

class TestMCPConnectivity:
    """测试 MCP Server 连通性及工具列表"""

    async def test_mcp_url_configured(self):
        """检查 MCP_SERVER_URL 是否已配置"""
        from src.config.settings import get_settings
        settings = get_settings()
        url = settings.mcp.mcp_server_url
        print(f"\n[MCP] MCP_SERVER_URL: {url or '未配置'}")
        assert url, "MCP_SERVER_URL 未配置，请在 .env 中设置"
        assert settings.mcp.is_configured, "is_configured 返回 False"
        print("[MCP] 配置检查通过 ✓")

    async def test_mcp_list_tools(self):
        """连接 MCP Server 并获取工具列表"""
        from src.config.settings import get_settings
        from pydantic_ai.mcp import MCPServerStreamableHTTP

        settings = get_settings()
        url = settings.mcp.mcp_server_url
        if not url:
            pytest.skip("MCP_SERVER_URL 未配置")

        print(f"\n[MCP] 连接 MCP Server: {url}")
        server = MCPServerStreamableHTTP(url=url)

        try:
            async with server:
                tools = await server.list_tools()
                print(f"[MCP] 获取到工具数量: {len(tools)}")
                for t in tools:
                    print(f"  - {t.name}: {getattr(t, 'description', '')[:80]}")
                assert len(tools) > 0, "MCP Server 返回了空工具列表"
                print("[MCP] 工具列表获取成功 ✓")
        except Exception as e:
            pytest.fail(f"MCP 连接失败: {type(e).__name__}: {e}")

    async def test_mcp_toolsets_from_config(self):
        """通过项目封装的 create_mcp_servers_from_config 验证"""
        from src.mcp.client import create_mcp_servers_from_config
        from src.config.settings import get_settings

        settings = get_settings()
        if not settings.mcp.is_configured:
            pytest.skip("MCP 未配置")

        servers = create_mcp_servers_from_config()
        print(f"\n[MCP] 创建 server 实例数: {len(servers)}")
        assert len(servers) > 0, "create_mcp_servers_from_config 返回空列表"

        # 逐个连接并列出工具
        for server in servers:
            try:
                async with server:
                    tools = await server.list_tools()
                    print(f"[MCP] server={server.url} tools={len(tools)}")
                    for t in tools:
                        print(f"  - {t.name}")
                    assert len(tools) > 0, f"server {server.url} 返回空工具列表"
            except Exception as e:
                pytest.fail(f"server {getattr(server, 'url', '?')} 连接失败: {e}")

        print("[MCP] 所有 server 工具列表获取成功 ✓")


# ============================================================
# 工具函数
# ============================================================

def _print_result(name: str, result) -> None:
    status = "✓" if result.success else "✗"
    print(f"\n[{name}] {status} exit_code={result.exit_code}")
    if result.stdout:
        print(f"  stdout: {result.stdout[:300]}")
    if result.stderr:
        print(f"  stderr: {result.stderr[:300]}")


def _print_worker_result(name: str, result) -> None:
    status = "✓" if result.success else "✗"
    print(f"\n[{name}] {status}")
    if result.data:
        import json
        try:
            print(f"  data: {json.dumps(result.data, ensure_ascii=False)[:300]}")
        except Exception:
            print(f"  data: {str(result.data)[:300]}")
    if result.error:
        print(f"  error: {result.error}")
