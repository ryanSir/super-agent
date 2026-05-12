from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .acceptance.e2e import run_local_e2e
from .core.audit import list_audit_records
from .core.credentials import configure_credential, list_credentials, test_credential
from .core.gateway import invoke_capability
from .core.observability import list_runtime_events
from .developer_tooling.packager import build_package
from .developer_tooling.publisher import publish_plugin
from .developer_tooling.validator import validate_plugin
from .management.manager import (
    disable_plugin,
    enable_plugin,
    install_plugin,
    list_capabilities,
    list_installed,
    uninstall_plugin,
)
from .runtime_host import runtime_health, start_runtime, stop_runtime
from .runtimes.data_source_runtime import list_data_sources
from .runtimes.mcp_runtime import list_mcp_tools
from .runtimes.skill_runtime import list_agent_skills, render_skill_context
from .shared.errors import PackageError, PluginPocError, PublishError, ValidationError


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    # argv=None 时 argparse 自动读取 sys.argv[1:]（跳过程序名本身）
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            result = validate_plugin(args.plugin_dir)
            _print_json(
                {
                    "status": "ok",
                    "plugin_id": result.manifest["id"],
                    "version": result.manifest["version"],
                    # relative_to 把绝对路径转回相对路径，as_posix 统一用 / 分隔符（跨平台）
                    "referenced_files": [
                        path.relative_to(result.plugin_dir).as_posix() for path in result.referenced_files
                    ],
                }
            )
            return 0  # 0 = 成功，Unix 惯例

        if args.command == "package":
            result = build_package(args.plugin_dir, args.output)
            # asdict 把 dataclass 转成普通字典，再经 _serializable 处理 Path 等不可序列化的类型
            _print_json(_serializable(asdict(result)))
            return 0

        if args.command == "publish":
            result = publish_plugin(args.plugin_dir, args.registry, force=args.force)
            _print_json(_serializable(asdict(result)))
            return 0

        if args.command == "install":
            result = install_plugin(args.registry, args.state, args.plugin_id, args.version)
            _print_json({"status": "ok", "installed": result})
            return 0

        if args.command == "enable":
            result = enable_plugin(args.state, args.plugin_id, args.version, args.workspace, args.agent)
            _print_json({"status": "ok", "enabled": result})
            return 0

        if args.command == "disable":
            result = disable_plugin(args.state, args.plugin_id, args.version, args.workspace, args.agent)
            # **result 把 result 字典的所有键值展开合并进响应
            _print_json({"status": "ok", **result})
            return 0

        if args.command == "uninstall":
            result = uninstall_plugin(args.state, args.plugin_id, args.version)
            _print_json({"status": "ok", **result})
            return 0

        if args.command == "list-installed":
            result = list_installed(args.state)
            _print_json({"status": "ok", "plugins": result})
            return 0

        if args.command == "list-capabilities":
            result = list_capabilities(args.state, args.workspace, args.agent)
            _print_json({"status": "ok", "capabilities": result})
            return 0

        if args.command == "invoke":
            input_data = _parse_json_input(args.input)
            result = invoke_capability(
                args.state,
                args.workspace,
                args.agent,
                args.capability_id,
                input_data,
                user=args.user,
                confirm_sensitive=args.confirm_sensitive,
                timeout_ms=args.timeout_ms,
            )
            # 失败时输出到 stderr，方便调用方用管道区分正常输出和错误输出
            _print_json(result.to_dict(), stderr=not result.success)
            return 0 if result.success else 1  # 1 = 业务失败

        if args.command == "configure-credential":
            values = _parse_json_input(args.values)
            result = configure_credential(args.state, args.plugin_id, args.version, args.workspace, values)
            _print_json({"status": "ok", "credential": result})
            return 0

        if args.command == "list-credentials":
            result = list_credentials(args.state)
            _print_json({"status": "ok", "credentials": result})
            return 0

        if args.command == "test-credential":
            result = test_credential(args.state, args.plugin_id, args.version, args.workspace)
            _print_json(
                {"status": "ok" if result["ok"] else "error", "credential_test": result},
                stderr=not result["ok"],
            )
            return 0 if result["ok"] else 1

        if args.command == "list-audit":
            result = list_audit_records(args.state)
            _print_json({"status": "ok", "records": result})
            return 0

        if args.command == "mcp-list-tools":
            result = list_mcp_tools(args.endpoint)
            _print_json({"status": "ok", "tools": result})
            return 0

        if args.command == "list-skills":
            result = list_agent_skills(
                args.state,
                args.workspace,
                args.agent,
                include_content=args.include_content,
            )
            _print_json({"status": "ok", "skills": result})
            return 0

        if args.command == "render-skill-context":
            result = render_skill_context(args.state, args.workspace, args.agent)
            _print_json({"status": "ok", "context": result})
            return 0

        if args.command == "list-data-sources":
            result = list_data_sources(args.state, args.workspace, args.agent)
            _print_json({"status": "ok", "data_sources": result})
            return 0

        if args.command == "start-runtime":
            result = start_runtime(args.state, args.plugin_id, args.version, args.mode)
            _print_json({"status": "ok", "runtime": result})
            return 0

        if args.command == "stop-runtime":
            result = stop_runtime(args.state, args.plugin_id, args.version)
            _print_json({"status": "ok", "runtime": result})
            return 0

        if args.command == "runtime-health":
            result = runtime_health(args.state, args.plugin_id, args.version)
            _print_json(result)
            return 0

        if args.command == "list-events":
            result = list_runtime_events(args.state)
            _print_json({"status": "ok", "events": result})
            return 0

        if args.command == "run-e2e":
            result = run_local_e2e(args.plugin_dir, args.registry, args.state)
            _print_json(result, stderr=result["status"] != "ok")
            return 0 if result["status"] == "ok" else 1

        parser.print_help()
        return 2  # 2 = 用法错误（没有匹配到任何子命令）
    except ValidationError as exc:
        # ValidationError 携带多条错误信息，直接输出列表
        _print_json({"status": "error", "errors": exc.errors}, stderr=True)
        return 1
    except (PackageError, PublishError, PluginPocError) as exc:
        _print_json({"status": "error", "errors": [str(exc)]}, stderr=True)
        return 1
    except ValueError as exc:
        # JSON 输入解析失败等参数错误
        _print_json({"status": "error", "errors": [str(exc)]}, stderr=True)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    # prog="plugin" 只影响 --help 的显示名称，实际运行仍用 python -m plugin_poc.cli
    parser = argparse.ArgumentParser(prog="plugin")
    # dest="command" → 用户输入的子命令名存到 args.command
    # required=True  → 不写子命令直接报错退出
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- 开发者工具：校验 / 打包 / 发布 ---

    validate_parser = subparsers.add_parser("validate", help="validate a plugin directory")
    validate_parser.add_argument("plugin_dir")  # 位置参数，必填

    package_parser = subparsers.add_parser("package", help="build a plugin package")
    package_parser.add_argument("plugin_dir")
    package_parser.add_argument("--output", default=None)  # 可选，不填则输出到默认路径

    publish_parser = subparsers.add_parser("publish", help="publish a plugin to a local registry")
    publish_parser.add_argument("plugin_dir")
    publish_parser.add_argument("--registry", required=True)
    publish_parser.add_argument("--force", action="store_true")  # 开关型参数，写了就是 True

    # --- 插件生命周期管理：安装 / 启用 / 禁用 / 卸载 ---

    install_parser = subparsers.add_parser("install", help="install a plugin from local registry")
    install_parser.add_argument("plugin_id")
    install_parser.add_argument("--version", required=True)
    install_parser.add_argument("--registry", required=True)
    install_parser.add_argument("--state", required=True)  # state 是存储插件状态的目录路径

    enable_parser = subparsers.add_parser("enable", help="enable an installed plugin for a workspace and agent")
    enable_parser.add_argument("plugin_id")
    enable_parser.add_argument("--version", required=True)
    enable_parser.add_argument("--state", required=True)
    enable_parser.add_argument("--workspace", required=True)  # 租户/工作空间维度
    enable_parser.add_argument("--agent", required=True)      # Agent 维度，同一插件可按 agent 粒度开关

    disable_parser = subparsers.add_parser("disable", help="disable a plugin for a workspace and agent")
    disable_parser.add_argument("plugin_id")
    disable_parser.add_argument("--version", required=True)
    disable_parser.add_argument("--state", required=True)
    disable_parser.add_argument("--workspace", required=True)
    disable_parser.add_argument("--agent", required=True)

    uninstall_parser = subparsers.add_parser("uninstall", help="uninstall a plugin version")
    uninstall_parser.add_argument("plugin_id")
    uninstall_parser.add_argument("--version", required=True)
    uninstall_parser.add_argument("--state", required=True)

    list_installed_parser = subparsers.add_parser("list-installed", help="list installed plugins")
    list_installed_parser.add_argument("--state", required=True)

    list_capabilities_parser = subparsers.add_parser("list-capabilities", help="list enabled capabilities")
    list_capabilities_parser.add_argument("--state", required=True)
    list_capabilities_parser.add_argument("--workspace", required=True)
    list_capabilities_parser.add_argument("--agent", required=True)

    # --- 能力调用网关 ---

    invoke_parser = subparsers.add_parser("invoke", help="invoke an enabled capability")
    invoke_parser.add_argument("capability_id")
    invoke_parser.add_argument("--state", required=True)
    invoke_parser.add_argument("--workspace", required=True)
    invoke_parser.add_argument("--agent", required=True)
    invoke_parser.add_argument("--user", default="anonymous")
    invoke_parser.add_argument("--confirm-sensitive", action="store_true")  # 敏感操作需用户二次确认
    invoke_parser.add_argument("--input", default="{}")       # JSON 字符串，传给能力的入参
    invoke_parser.add_argument("--timeout-ms", type=int, default=None)  # type=int 自动把字符串转整数

    # --- 凭证管理 ---

    configure_credential_parser = subparsers.add_parser("configure-credential", help="configure plugin credential")
    configure_credential_parser.add_argument("plugin_id")
    configure_credential_parser.add_argument("--version", required=True)
    configure_credential_parser.add_argument("--state", required=True)
    configure_credential_parser.add_argument("--workspace", required=True)
    configure_credential_parser.add_argument("--values", required=True)  # JSON 字符串，存 token/key 等

    list_credentials_parser = subparsers.add_parser("list-credentials", help="list configured credentials")
    list_credentials_parser.add_argument("--state", required=True)

    test_credential_parser = subparsers.add_parser("test-credential", help="test configured credential presence")
    test_credential_parser.add_argument("plugin_id")
    test_credential_parser.add_argument("--version", required=True)
    test_credential_parser.add_argument("--state", required=True)
    test_credential_parser.add_argument("--workspace", required=True)

    # --- 审计 ---

    list_audit_parser = subparsers.add_parser("list-audit", help="list invocation audit records")
    list_audit_parser.add_argument("--state", required=True)

    # --- MCP 工具 ---

    mcp_list_tools_parser = subparsers.add_parser(
        "mcp-list-tools",
        help="list tools from a Streamable HTTP MCP endpoint",
    )
    mcp_list_tools_parser.add_argument("--endpoint", required=True)

    # --- Skill / 数据源 ---

    list_skills_parser = subparsers.add_parser("list-skills", help="list enabled skill capabilities")
    list_skills_parser.add_argument("--state", required=True)
    list_skills_parser.add_argument("--workspace", required=True)
    list_skills_parser.add_argument("--agent", required=True)
    list_skills_parser.add_argument("--include-content", action="store_true")  # 是否返回 SKILL.md 全文

    render_skill_context_parser = subparsers.add_parser(
        "render-skill-context",
        help="render enabled plugin skills as agent context",
    )
    render_skill_context_parser.add_argument("--state", required=True)
    render_skill_context_parser.add_argument("--workspace", required=True)
    render_skill_context_parser.add_argument("--agent", required=True)

    list_data_sources_parser = subparsers.add_parser("list-data-sources", help="list enabled data sources")
    list_data_sources_parser.add_argument("--state", required=True)
    list_data_sources_parser.add_argument("--workspace", required=True)
    list_data_sources_parser.add_argument("--agent", required=True)

    # --- 运行时管理 ---

    start_runtime_parser = subparsers.add_parser("start-runtime", help="start or register plugin runtime host")
    start_runtime_parser.add_argument("plugin_id")
    start_runtime_parser.add_argument("--version", required=True)
    start_runtime_parser.add_argument("--state", required=True)
    start_runtime_parser.add_argument("--mode", default="local_daemon")  # 运行模式：local_daemon/remote/sidecar 等

    stop_runtime_parser = subparsers.add_parser("stop-runtime", help="stop plugin runtime host")
    stop_runtime_parser.add_argument("plugin_id")
    stop_runtime_parser.add_argument("--version", required=True)
    stop_runtime_parser.add_argument("--state", required=True)

    runtime_health_parser = subparsers.add_parser("runtime-health", help="show runtime host health")
    runtime_health_parser.add_argument("--state", required=True)
    runtime_health_parser.add_argument("--plugin-id", default=None)  # 不填则查所有运行时
    runtime_health_parser.add_argument("--version", default=None)

    list_events_parser = subparsers.add_parser("list-events", help="list runtime observability events")
    list_events_parser.add_argument("--state", required=True)

    # --- 端到端验收测试 ---

    run_e2e_parser = subparsers.add_parser("run-e2e", help="run local end-to-end plugin POC verification")
    run_e2e_parser.add_argument("--plugin-dir", required=True)
    run_e2e_parser.add_argument("--registry", required=True)
    run_e2e_parser.add_argument("--state", required=True)
    return parser


def _print_json(data: dict[str, Any], stderr: bool = False) -> None:
    # 错误输出走 stderr，正常输出走 stdout，方便调用方用管道区分
    stream = sys.stderr if stderr else sys.stdout
    # ensure_ascii=False 保留中文，default=str 兜底处理 Path 等不可序列化类型
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str), file=stream)


def _serializable(data: Any) -> Any:
    # 递归把 dataclass 转出的字典里的 Path 对象转成字符串，使其可以被 json.dumps 序列化
    if isinstance(data, Path):
        return str(data)
    if isinstance(data, dict):
        return {key: _serializable(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_serializable(item) for item in data]
    if isinstance(data, tuple):
        return [_serializable(item) for item in data]
    return data


def _parse_json_input(raw: str) -> dict[str, Any]:
    # 把命令行传入的 JSON 字符串解析成字典，非法格式统一转成 ValueError 向上抛
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON input: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


if __name__ == "__main__":
    # raise SystemExit 把返回码传给操作系统（0=成功，非0=失败），脚本方式运行时生效
    raise SystemExit(main())
