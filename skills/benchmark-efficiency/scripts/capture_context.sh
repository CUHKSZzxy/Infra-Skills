#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_SCRIPT="${SCRIPT_DIR}/../../../scripts/capture_deployment_context.sh"

if [ ! -x "${REPO_SCRIPT}" ]; then
    echo "capture_deployment_context.sh not found or not executable: ${REPO_SCRIPT}" >&2
    exit 1
fi

exec "${REPO_SCRIPT}" "$@"
