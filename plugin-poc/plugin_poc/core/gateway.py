from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..management.manager import list_capabilities
from ..runtimes.data_source_runtime import query_data_source
from ..runtimes.mcp_runtime import invoke_mcp
from ..runtimes.openapi_runtime import invoke_openapi
from .audit import write_audit_record
from .observability import write_runtime_event
from .policy import check_invocation_policy


@dataclass(frozen=True)
class InvocationResult:
    success: bool
    capability_id: str
    runtime: str | None
    output: dict[str, Any] | None
    error: dict[str, Any] | None
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def invoke_capability(
    state_dir: str | Path,
    workspace: str,
    agent: str,
    capability_id: str,
    input_data: dict[str, Any],
    user: str = "anonymous",
    confirm_sensitive: bool = False,
    timeout_ms: int | None = None,
) -> InvocationResult:
    started = time.perf_counter()
    capability = _find_capability(state_dir, workspace, agent, capability_id)
    if capability is None:
        return _audited_failure(
            state_dir,
            workspace,
            agent,
            user,
            capability_id,
            input_data,
            "capability_not_found",
            "capability is not enabled for workspace/agent",
            started,
        )

    capability_type = capability.get("type")
    if capability_type not in {"tool", "openapi", "mcp", "data_source"}:
        return _audited_failure(
            state_dir,
            workspace,
            agent,
            user,
            capability_id,
            input_data,
            "unsupported_capability_type",
            f"supported capability types are tool, openapi, mcp and data_source, got {capability_type}",
            started,
            capability=capability,
        )

    timeout_error = _check_simulated_timeout(input_data, timeout_ms)
    if timeout_error:
        return _audited_failure(
            state_dir,
            workspace,
            agent,
            user,
            capability_id,
            input_data,
            timeout_error["code"],
            timeout_error["message"],
            started,
            capability=capability,
        )

    policy_error = check_invocation_policy(state_dir, capability, confirm_sensitive)
    if policy_error:
        return _audited_failure(
            state_dir,
            workspace,
            agent,
            user,
            capability_id,
            input_data,
            policy_error["code"],
            policy_error["message"],
            started,
            capability=capability,
        )

    if capability_type == "tool":
        output, error, runtime = _invoke_tool(capability, input_data)
    elif capability_type == "openapi":
        output, error = invoke_openapi(capability, input_data)
        runtime = "mock_openapi"
    elif capability_type == "mcp":
        output, error = invoke_mcp(capability, input_data)
        runtime = "streamable_http_mcp"
    else:
        output, error = query_data_source(capability, input_data)
        runtime = "local_data_source"

    if error:
        return _audited_failure(
            state_dir,
            workspace,
            agent,
            user,
            capability_id,
            input_data,
            error["code"],
            error["message"],
            started,
            details=error.get("details"),
            capability=capability,
            runtime=runtime,
        )

    result = InvocationResult(
        success=True,
        capability_id=capability_id,
        runtime=runtime,
        output=output,
        error=None,
        duration_ms=_duration_ms(started),
    )
    write_audit_record(
        state_dir,
        capability_id=capability_id,
        workspace=workspace,
        agent=agent,
        user=user,
        success=True,
        error_code=None,
        input_data=input_data,
        duration_ms=result.duration_ms,
    )
    write_runtime_event(
        state_dir,
        event_type="capability_invocation",
        capability=capability,
        runtime=runtime,
        success=True,
        duration_ms=result.duration_ms,
    )
    return result


def _find_capability(
    state_dir: str | Path,
    workspace: str,
    agent: str,
    capability_id: str,
) -> dict[str, Any] | None:
    for capability in list_capabilities(state_dir, workspace, agent):
        if capability.get("capability_id") == capability_id:
            return capability
    return None


def _missing_required_fields(capability: dict[str, Any], input_data: dict[str, Any]) -> list[str]:
    input_schema = capability.get("input_schema") or {}
    required = input_schema.get("required") or []
    return [field for field in required if field not in input_data]


def _invoke_tool(
    capability: dict[str, Any],
    input_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    missing = _missing_required_fields(capability, input_data)
    if missing:
        return (
            None,
            {
                "code": "invalid_input",
                "message": f"missing required input fields: {', '.join(missing)}",
                "details": {"missing": missing},
            },
            "local_mock_tool",
        )
    output = {
        "message": "mock tool invocation succeeded",
        "tool": capability.get("name"),
        "input": input_data,
        "source": capability.get("source"),
    }
    return output, None, "local_mock_tool"


def _failure(
    capability_id: str,
    code: str,
    message: str,
    started: float,
    details: dict[str, Any] | None = None,
) -> InvocationResult:
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return InvocationResult(
        success=False,
        capability_id=capability_id,
        runtime=None,
        output=None,
        error=error,
        duration_ms=_duration_ms(started),
    )


def _audited_failure(
    state_dir: str | Path,
    workspace: str,
    agent: str,
    user: str,
    capability_id: str,
    input_data: dict[str, Any],
    code: str,
    message: str,
    started: float,
    details: dict[str, Any] | None = None,
    capability: dict[str, Any] | None = None,
    runtime: str | None = None,
) -> InvocationResult:
    result = _failure(capability_id, code, message, started, details)
    write_audit_record(
        state_dir,
        capability_id=capability_id,
        workspace=workspace,
        agent=agent,
        user=user,
        success=False,
        error_code=code,
        input_data=input_data,
        duration_ms=result.duration_ms,
    )
    if capability is not None:
        write_runtime_event(
            state_dir,
            event_type="capability_invocation",
            capability=capability,
            runtime=runtime,
            success=False,
            error_code=code,
            duration_ms=result.duration_ms,
        )
    return result


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _check_simulated_timeout(input_data: dict[str, Any], timeout_ms: int | None) -> dict[str, str] | None:
    if timeout_ms is None:
        return None
    simulated_delay = int(input_data.get("simulate_delay_ms", 0))
    if simulated_delay > timeout_ms:
        return {
            "code": "runtime_timeout",
            "message": f"simulated runtime delay {simulated_delay}ms exceeds timeout {timeout_ms}ms",
        }
    return None
