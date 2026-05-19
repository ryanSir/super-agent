#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from plugin_developer.packager import package_plugin
from plugin_developer.publisher import publish_package
from plugin_developer.validator import validate_plugin


def main() -> int:
    parser = argparse.ArgumentParser(prog="pluginctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("plugin_dir", type=Path)

    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("plugin_dir", type=Path)
    package_parser.add_argument("--out", type=Path, required=True)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("package_path", type=Path)
    publish_parser.add_argument("--registry-url", required=True)
    publish_parser.add_argument("--timeout", type=float, default=10.0)

    args = parser.parse_args()
    if args.command == "validate":
        result = validate_plugin(args.plugin_dir)
        print(result.model_dump_json(indent=2))
        return 0 if result.valid else 1
    if args.command == "package":
        result = package_plugin(args.plugin_dir, args.out)
        print(json.dumps(_dataclass_dict(result), indent=2, default=str))
        return 0
    if args.command == "publish":
        result = publish_package(
            args.registry_url,
            args.package_path,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(_dataclass_dict(result), indent=2))
        return 0
    return 2


def _dataclass_dict(value: object) -> dict[str, object]:
    return {key: getattr(value, key) for key in value.__dataclass_fields__}


if __name__ == "__main__":
    raise SystemExit(main())
