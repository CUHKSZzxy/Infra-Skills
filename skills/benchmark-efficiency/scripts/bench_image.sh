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
IMAGE_BENCH_EXTRA_ARGS=()

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

BENCH_STREAM_LOGS="${BENCH_STREAM_LOGS:-0}"
IMAGE_BENCH_DRY_RUN="${IMAGE_BENCH_DRY_RUN:-0}"
IMAGE_API_BACKEND_LABEL="${IMAGE_API_BACKEND_LABEL:-lmdeploy-chat}"
IMAGE_RANGE_RATIO="${IMAGE_RANGE_RATIO:-1}"
IMAGE_FORMAT="${IMAGE_FORMAT:-jpeg}"
IMAGE_CONTENT="${IMAGE_CONTENT:-random}"

if [ ! -f "${PROFILE_RESTFUL_API}" ]; then
    echo "PROFILE_RESTFUL_API not found: ${PROFILE_RESTFUL_API}" >&2
    exit 1
fi
if [ "${#IMAGE_INPUT_LENS[@]}" -ne "${#IMAGE_OUTPUT_LENS[@]}" ]; then
    echo "IMAGE_INPUT_LENS and IMAGE_OUTPUT_LENS must have the same length" >&2
    exit 1
fi
if [ "${#IMAGE_INPUT_LENS[@]}" -ne "${#IMAGE_NUM_PROMPTS[@]}" ]; then
    echo "IMAGE_INPUT_LENS and IMAGE_NUM_PROMPTS must have the same length" >&2
    exit 1
fi
if [ "${#IMAGE_INPUT_LENS[@]}" -ne "${#IMAGE_RESOLUTIONS[@]}" ]; then
    echo "IMAGE_INPUT_LENS and IMAGE_RESOLUTIONS must have the same length" >&2
    exit 1
fi
if [ "${#IMAGE_INPUT_LENS[@]}" -ne "${#IMAGE_COUNTS[@]}" ]; then
    echo "IMAGE_INPUT_LENS and IMAGE_COUNTS must have the same length" >&2
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

for idx in "${!IMAGE_INPUT_LENS[@]}"; do
    IN_LEN="${IMAGE_INPUT_LENS[$idx]}"
    OUT_LEN="${IMAGE_OUTPUT_LENS[$idx]}"
    NUM_PROMPT="${IMAGE_NUM_PROMPTS[$idx]}"
    IMAGE_RESOLUTION="${IMAGE_RESOLUTIONS[$idx]}"
    IMAGE_COUNT="${IMAGE_COUNTS[$idx]}"
    IMAGE_LABEL="img${IMAGE_COUNT}-${IMAGE_RESOLUTION}-${IMAGE_FORMAT}-${IMAGE_CONTENT}"
    LOG_FILE="${LOG_DIR}/${DATE}_${MODEL_ABBR}_${SUFFIX}_${IMAGE_LABEL}_image_out_${OUT_LEN}_prompts_${NUM_PROMPT}.log"

    echo "Running image benchmark | in_len=${IN_LEN} out_len=${OUT_LEN} prompts=${NUM_PROMPT} images=${IMAGE_COUNT} resolution=${IMAGE_RESOLUTION} log=${LOG_FILE}"

    CMD=(
        "${PYTHON_BIN}" "${PROFILE_RESTFUL_API}"
        --backend "${IMAGE_API_BACKEND_LABEL}"
        --dataset-name image
        --model "${MODEL_ABBR}"
        --model-path "${MODEL_PATH}"
        --tokenizer "${MODEL_PATH}"
        --host "${BENCH_HOST:-127.0.0.1}"
        --port "${PORT}"
        --num-prompts "${NUM_PROMPT}"
        --random-input-len "${IN_LEN}"
        --random-output-len "${OUT_LEN}"
        --random-range-ratio "${IMAGE_RANGE_RATIO}"
        --image-count "${IMAGE_COUNT}"
        --image-resolution "${IMAGE_RESOLUTION}"
        --image-format "${IMAGE_FORMAT}"
        --image-content "${IMAGE_CONTENT}"
        --trust-remote-code
    )
    CMD+=("${BENCH_EXTRA_ARGS[@]}" "${IMAGE_BENCH_EXTRA_ARGS[@]}")

    printf '%q ' "${CMD[@]}" > "${LOG_FILE%.log}.cmd"
    printf '\n' >> "${LOG_FILE%.log}.cmd"

    if [ "${IMAGE_BENCH_DRY_RUN}" = "1" ]; then
        printf '%q ' "${CMD[@]}"
        printf '\n'
    elif [ "${BENCH_STREAM_LOGS}" = "1" ]; then
        "${CMD[@]}" 2>&1 | tee "${LOG_FILE}"
    else
        "${CMD[@]}" > "${LOG_FILE}" 2>&1
    fi
done
