"""沙箱 IPC 通信和配置测试"""

from src.workers.sandbox.ipc import parse_jsonl, ipc_to_a2ui_events, get_new_messages
from src.workers.sandbox.pi_agent_config import (
    ATOMIC_TOOLS,
    PI_STATE_FILE,
    build_env_vars,
    build_startup_command,
)
from src.schemas.sandbox import IPCMessage, PiAgentPhase


class TestIPCParsing:
    def test_parse_valid_jsonl(self):
        """pi v0.62+ 格式：message_start 包含 assistant 消息"""
        raw = (
            '{"type": "message_start", "message": {"role": "assistant", "content": [{"type": "text", "text": "分析需求"}]}}\n'
            '{"type": "message_start", "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "input": {"cmd": "ls"}}]}}\n'
        )
        messages = parse_jsonl(raw)
        assert len(messages) >= 2
        phases = [m.phase for m in messages]
        assert PiAgentPhase.THOUGHT in phases
        assert PiAgentPhase.ACTION in phases

    def test_parse_empty_string(self):
        assert parse_jsonl("") == []

    def test_parse_invalid_json_skipped(self):
        raw = '{"type": "message_start", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}\ninvalid json\n{"type": "tool_result", "content": "done"}\n'
        messages = parse_jsonl(raw)
        assert len(messages) == 2

    def test_get_new_messages(self):
        msgs = [
            IPCMessage(phase=PiAgentPhase.THOUGHT, content="1"),
            IPCMessage(phase=PiAgentPhase.ACTION, content="2"),
            IPCMessage(phase=PiAgentPhase.OBSERVATION, content="3"),
        ]
        new = get_new_messages(msgs, 1)
        assert len(new) == 2
        assert new[0].content == "2"


class TestIPCToA2UI:
    def test_thought_maps_to_process_update(self):
        msgs = [IPCMessage(phase=PiAgentPhase.THOUGHT, content="思考中")]
        events = ipc_to_a2ui_events(msgs, trace_id="t-1")
        assert len(events) == 1
        assert events[0]["event_type"] == "process_update"
        assert events[0]["phase"] == "thinking"

    def test_final_answer_maps_to_text_stream(self):
        msgs = [IPCMessage(phase=PiAgentPhase.FINAL_ANSWER, content="完成")]
        events = ipc_to_a2ui_events(msgs, trace_id="t-1")
        assert len(events) == 1
        assert events[0]["event_type"] == "text_stream"
        assert events[0]["is_final"] is True

    def test_action_includes_tool_info(self):
        msgs = [IPCMessage(phase=PiAgentPhase.ACTION, tool_name="Bash", tool_input={"cmd": "ls"})]
        events = ipc_to_a2ui_events(msgs)
        assert events[0]["details"]["tool_name"] == "Bash"


class TestPiAgentConfig:
    def test_atomic_tools(self):
        assert ATOMIC_TOOLS == "read,bash,edit,write"

    def test_state_file(self):
        assert PI_STATE_FILE == ".pi_state.jsonl"

    def test_build_env_vars(self):
        env = build_env_vars("token-123", "http://proxy:8080")
        assert env["OPENAI_API_KEY"] == "token-123"
        assert env["OPENAI_BASE_URL"] == "http://proxy:8080"

    def test_build_env_vars_with_extra(self):
        env = build_env_vars("t", "u", extra_env={"CUSTOM": "val"})
        assert env["CUSTOM"] == "val"

    def test_build_startup_command(self):
        cmd = build_startup_command(
            work_dir="/home/user",
            instruction="生成图表",
            llm_token="tok",
            llm_base_url="http://proxy",
        )
        assert "pi --print --mode json" in cmd
        assert "生成图表" in cmd
        assert "tok" in cmd
