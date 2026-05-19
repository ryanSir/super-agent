#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN_DIR="$ROOT_DIR/plugin-platform"

export PYTHONPATH="$PLUGIN_DIR/packages/plugin-contracts:$PLUGIN_DIR/developer-tools/sdk:$PLUGIN_DIR/services/plugin-management-service:$PLUGIN_DIR/services/plugin-core-service:$PLUGIN_DIR/services/plugin-runtime-service:${PYTHONPATH:-}"

cd "$ROOT_DIR"
exec uvicorn plugin_core_service.api.app:app --host 127.0.0.1 --port 8017 --reload
