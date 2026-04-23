#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(pwd)"
DESIGNS_FILE="${SCRIPT_DIR}/../references/designs.txt"

usage() {
  cat <<'EOF'
Usage:
  install-design.sh --list
  install-design.sh <style>

Examples:
  install-design.sh vercel
  install-design.sh claude
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

if [[ "$1" == "--list" ]]; then
  cat "${DESIGNS_FILE}"
  exit 0
fi

STYLE="$1"

if ! grep -Fxq "${STYLE}" "${DESIGNS_FILE}"; then
  echo "Unknown style: ${STYLE}" >&2
  echo "Run 'install-design.sh --list' to see supported slugs." >&2
  exit 1
fi

if [[ -f "${ROOT_DIR}/DESIGN.md" ]]; then
  echo "DESIGN.md already exists in ${ROOT_DIR}." >&2
  echo "Refusing to overwrite it. Remove or rename it first if you want a new preset." >&2
  exit 1
fi

exec npx getdesign@latest add "${STYLE}"
