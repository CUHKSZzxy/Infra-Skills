#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-$(dirname "$0")/lmdeploy_config.sh}"
TIMEOUT_SECONDS="${2:-600}"

if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Config file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

START_TS="$(date +%s)"
URL="http://${BENCH_HOST:-127.0.0.1}:${PORT}/v1/models"

while true; do
    if curl --noproxy '*' -fsS "${URL}" >/tmp/lmdeploy_wait_server_models.json 2>/tmp/lmdeploy_wait_server.err; then
        ELAPSED="$(( $(date +%s) - START_TS ))"
        echo "ready_after=${ELAPSED}s"
        cat /tmp/lmdeploy_wait_server_models.json
        echo
        exit 0
    fi
    if [ "$(( $(date +%s) - START_TS ))" -ge "${TIMEOUT_SECONDS}" ]; then
        echo "timeout waiting for ${URL}" >&2
        if [ -s /tmp/lmdeploy_wait_server.err ]; then
            cat /tmp/lmdeploy_wait_server.err >&2
        fi
        exit 1
    fi
    sleep 5
done
