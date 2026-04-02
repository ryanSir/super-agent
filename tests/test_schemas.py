"""Schema 序列化/反序列化测试"""

from src.schemas.agent import (
    ExecutionDAG,
    OrchestratorOutput,
    RiskLevel,
    TaskNode,
    TaskStatus,
    TaskType,
    WorkerResult,
)
from src.schemas.api import EventType, QueryRequest, QueryResponse, StreamEvent
from src.schemas.a2ui import (
    A2UIEventType,
    ArtifactPreview,
    DataChart,
    ProcessUpdate,
    RenderWidget,
    TextStream,
)
from src.schemas.sandbox import (
    Artifact,
    IPCMessage,
    PiAgentPhase,
    SandboxResult,
    SandboxState,
    SandboxStatus,
    SandboxTask,
)


class TestAgentSchemas:
    def test_task_node_creation(self):
        node = TaskNode(
            task_id="t1",
            task_type=TaskType.RAG_RETRIEVAL,
            description="检索专利",
        )
        assert node.task_id == "t1"
        assert node.risk_level == RiskLevel.SAFE
        assert node.status == TaskStatus.PENDING

    def test_execution_dag(self):
        tasks = [
            TaskNode(task_id="t1", task_type=TaskType.RAG_RETRIEVAL, description="检索"),
            TaskNode(task_id="t2", task_type=TaskType.SANDBOX_CODING, depends_on=["t1"], description="编码"),
        ]
        dag = ExecutionDAG(dag_id="dag-1", query="测试", tasks=tasks)

        assert len(dag.tasks) == 2
        assert len(dag.root_tasks) == 1
        assert dag.root_tasks[0].task_id == "t1"
        assert "t1" in dag.task_map

    def test_worker_result_serialization(self):
        result = WorkerResult(
            task_id="t1",
            success=True,
            data={"documents": [{"id": 1, "title": "专利A"}]},
        )
        d = result.model_dump()
        assert d["success"] is True
        assert d["data"]["documents"][0]["title"] == "专利A"

    def test_orchestrator_output(self):
        output = OrchestratorOutput(
            answer="分析完成",
            worker_results=[
                WorkerResult(task_id="t1", success=True, data="ok"),
            ],
            trace_id="trace-123",
        )
        assert output.answer == "分析完成"
        assert len(output.worker_results) == 1


class TestAPISchemas:
    def test_query_request_validation(self):
        req = QueryRequest(query="查找AI专利")
        assert req.mode == "auto"
        assert req.session_id is None

    def test_query_request_mode_validation(self):
        req = QueryRequest(query="test", mode="plan_and_execute")
        assert req.mode == "plan_and_execute"

    def test_stream_event(self):
        event = StreamEvent(
            event_type=EventType.TASK_STARTED,
            session_id="sess-1",
            data={"task_id": "t1"},
        )
        assert event.event_type == EventType.TASK_STARTED


class TestA2UISchemas:
    def test_render_widget(self):
        widget = RenderWidget(
            trace_id="trace-1",
            ui_component="PatentTrendChart",
            props={"title": "趋势图", "xAxis": ["1月", "2月"]},
        )
        assert widget.event_type == A2UIEventType.RENDER_WIDGET
        assert widget.ui_component == "PatentTrendChart"

    def test_process_update(self):
        update = ProcessUpdate(
            phase="thinking",
            status="in_progress",
            message="分析中...",
            progress=0.5,
        )
        assert update.progress == 0.5

    def test_data_chart(self):
        chart = DataChart(
            props={"title": "图表", "series": [{"data": [1, 2, 3]}]},
        )
        assert chart.ui_component == "DataChart"

    def test_text_stream(self):
        stream = TextStream(delta="Hello", is_final=False)
        assert stream.event_type == A2UIEventType.TEXT_STREAM


class TestSandboxSchemas:
    def test_sandbox_task(self):
        task = SandboxTask(
            task_id="st-1",
            instruction="生成趋势图",
            context_files={"data.json": '{"values": [1,2,3]}'},
            timeout=120,
        )
        assert task.timeout == 120
        assert "data.json" in task.context_files

    def test_ipc_message(self):
        msg = IPCMessage(
            phase=PiAgentPhase.THOUGHT,
            content="分析需求",
        )
        assert msg.phase == PiAgentPhase.THOUGHT

    def test_sandbox_result(self):
        result = SandboxResult(
            task_id="st-1",
            sandbox_id="sbx-123",
            success=True,
            final_answer="图表已生成",
            artifacts=[
                Artifact(filename="chart.html", content_type="text/html", size_bytes=1024),
            ],
        )
        assert len(result.artifacts) == 1
        assert result.artifacts[0].filename == "chart.html"
