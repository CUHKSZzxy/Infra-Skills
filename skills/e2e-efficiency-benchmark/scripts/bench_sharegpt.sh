#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-$(dirname "$0")/lmdeploy_config.sh}"
CUSTOM_LABEL="${2:-}"

if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Config file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

FEATURE_LABEL=""
BENCH_EXTRA_ARGS=()

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

BENCH_STREAM_LOGS="${BENCH_STREAM_LOGS:-0}"

if [ ! -f "${PROFILE_RESTFUL_API}" ]; then
    echo "PROFILE_RESTFUL_API not found: ${PROFILE_RESTFUL_API}" >&2
    exit 1
fi
if [ ! -f "${DATASET_PATH}" ]; then
    echo "DATASET_PATH not found: ${DATASET_PATH}" >&2
    exit 1
fi
if [ "${#OUT_LENS[@]}" -ne "${#NUM_PROMPTS[@]}" ]; then
    echo "OUT_LENS and NUM_PROMPTS must have the same length" >&2
    exit 1
fi

CONFIG_DIR="$(cd "$(dirname "${CONFIG_FILE}")" && pwd)"
LOG_DIR="${CONFIG_DIR}/${BENCH_LOG_DIR}"
DATE="$(date +%y%m%d_%H%M%S)"
mkdir -p "${LOG_DIR}"

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

for idx in "${!OUT_LENS[@]}"; do
    OUT_LEN="${OUT_LENS[$idx]}"
    NUM_PROMPT="${NUM_PROMPTS[$idx]}"
    LOG_FILE="${LOG_DIR}/${DATE}_${MODEL_ABBR}_${SUFFIX}_${DATASET_NAME}_out_${OUT_LEN}_prompts_${NUM_PROMPT}.log"

    echo "Running benchmark | out_len=${OUT_LEN} prompts=${NUM_PROMPT} log=${LOG_FILE}"

    CMD=(
        "${PYTHON_BIN}" "${PROFILE_RESTFUL_API}"
        --backend "${API_BACKEND_LABEL}"
        --dataset-name "${DATASET_NAME}"
        --dataset-path "${DATASET_PATH}"
        --model "${MODEL_ABBR}"
        --model-path "${MODEL_PATH}"
        --tokenizer "${MODEL_PATH}"
        --host "${BENCH_HOST:-127.0.0.1}"
        --port "${PORT}"
        --num-prompts "${NUM_PROMPT}"
        --trust-remote-code
    )
    if [ "${OUT_LEN}" != "None" ]; then
        CMD+=(--sharegpt-output-len "${OUT_LEN}")
    fi
    CMD+=("${BENCH_EXTRA_ARGS[@]}")

    if [ "${BENCH_STREAM_LOGS}" = "1" ]; then
        "${CMD[@]}" 2>&1 | tee "${LOG_FILE}"
    else
        "${CMD[@]}" > "${LOG_FILE}" 2>&1
    fi
done
