#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-$(dirname "$0")/lmdeploy_config.sh}"
CUSTOM_LABEL="${2:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Config file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

FEATURE_LABEL=""
LMDEPLOY_EXTRA_ARGS=()

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

SERVE_BACKGROUND="${SERVE_BACKGROUND:-0}"
SERVE_STREAM_LOGS="${SERVE_STREAM_LOGS:-0}"
CONTEXT_SUBDIR="${CONTEXT_SUBDIR:-context}"
CONTEXT_CAPTURE="${CONTEXT_CAPTURE:-1}"

CONFIG_DIR="$(cd "$(dirname "${CONFIG_FILE}")" && pwd)"
LOG_DIR="${CONFIG_DIR}/${SERVE_LOG_DIR}"
CONTEXT_DIR="${CONFIG_DIR}/${CONTEXT_SUBDIR}"
COMMAND_DIR="${CONTEXT_DIR}/commands"
DATE="$(date +%y%m%d_%H%M%S)"
mkdir -p "${LOG_DIR}" "${COMMAND_DIR}"

if [ "${CONTEXT_CAPTURE}" = "1" ]; then
    SOURCE_FOR_CONTEXT="${SOURCE_CHECKOUT:-${CONFIG_DIR}}"
    if ! bash "${SCRIPT_DIR}/capture_context.sh" "${CONFIG_DIR}" "${SOURCE_FOR_CONTEXT}" "${CONFIG_FILE}" > "${CONTEXT_DIR}/capture_context.log" 2>&1; then
        echo "WARNING: context capture failed; see ${CONTEXT_DIR}/capture_context.log" >&2
    fi
fi

QUANT_POLICY_ARG="${QUANT_POLICY}"
if [ "${QUANT_POLICY_ARG}" = "none" ]; then
    QUANT_POLICY_ARG="0"
fi

SUFFIX="tp${TENSOR_PARALLEL_SIZE}_dp${DATA_PARALLEL_SIZE}"
if [ -n "${FEATURE_LABEL}" ]; then
    SUFFIX="${SUFFIX}_feature-${FEATURE_LABEL}"
fi
KV_LABEL=""
if [ "${QUANT_POLICY_ARG}" != "0" ]; then
    KV_LABEL="kv${QUANT_POLICY_ARG}"
    SUFFIX="${SUFFIX}_${KV_LABEL}"
fi
if [ -n "${CUSTOM_LABEL}" ] && [ "${CUSTOM_LABEL}" != "${KV_LABEL}" ]; then
    SUFFIX="${SUFFIX}_${CUSTOM_LABEL}"
fi

LOG_FILE="${LOG_DIR}/${DATE}_${MODEL_ABBR}_${SUFFIX}_serve.log"
CMD_FILE="${LOG_FILE%.log}.cmd"
CONTEXT_CMD_FILE="${COMMAND_DIR}/$(basename "${CMD_FILE}")"

echo "Starting LMDeploy server"
echo "  model=${MODEL_PATH}"
echo "  backend=${BACKEND} tp=${TENSOR_PARALLEL_SIZE} dp_label=${DATA_PARALLEL_SIZE}"
echo "  quant_policy=${QUANT_POLICY_ARG} host=${HOST} port=${PORT}"
echo "  log=${LOG_FILE}"

CMD=(
    "${LMDEPLOY_BIN}" serve api_server
    "${MODEL_PATH}"
    --tp "${TENSOR_PARALLEL_SIZE}"
    --server-name "${HOST}"
    --server-port "${PORT}"
    --backend "${BACKEND}"
    --quant-policy "${QUANT_POLICY_ARG}"
    --model-name "${MODEL_ABBR}"
    --trust-remote-code
    "${LMDEPLOY_EXTRA_ARGS[@]}"
)

printf '%q ' "${CMD[@]}" > "${CMD_FILE}"
printf '\n' >> "${CMD_FILE}"
printf '%q ' "${CMD[@]}" > "${CONTEXT_CMD_FILE}"
printf '\n' >> "${CONTEXT_CMD_FILE}"

if [ "${SERVE_BACKGROUND}" = "1" ]; then
    if [ "${SERVE_STREAM_LOGS}" = "1" ]; then
        nohup "${CMD[@]}" 2>&1 | tee "${LOG_FILE}" &
    else
        nohup "${CMD[@]}" > "${LOG_FILE}" 2>&1 < /dev/null &
    fi
    SERVER_PID=$!
    echo "${SERVER_PID}" > "${LOG_FILE%.log}.pid"
    echo "server_pid=${SERVER_PID}"
    echo "pid_file=${LOG_FILE%.log}.pid"
elif [ "${SERVE_STREAM_LOGS}" = "1" ]; then
    "${CMD[@]}" 2>&1 | tee "${LOG_FILE}"
else
    "${CMD[@]}" > "${LOG_FILE}" 2>&1
fi
