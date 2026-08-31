#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: capture_deployment_context.sh RUN_DIR [SOURCE_CHECKOUT] [CONFIG_FILE]

Capture reproducibility context for a local accuracy or efficiency benchmark.
The script writes files under RUN_DIR/context by default. If CONFIG_FILE is
provided, it is sourced first and copied to context/config.sh.snapshot.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi

if [ "$#" -lt 1 ]; then
    usage >&2
    exit 2
fi

RUN_DIR="$1"
SOURCE_CHECKOUT="${2:-${SOURCE_CHECKOUT:-}}"
CONFIG_FILE="${3:-${CONFIG_FILE:-}}"

if [ -n "${CONFIG_FILE}" ] && [ ! -f "${CONFIG_FILE}" ]; then
    echo "CONFIG_FILE not found: ${CONFIG_FILE}" >&2
    exit 2
fi

if [ -n "${CONFIG_FILE}" ]; then
    # shellcheck source=/dev/null
    source "${CONFIG_FILE}"
fi

RUN_DIR_ABS="$(mkdir -p "${RUN_DIR}" && cd "${RUN_DIR}" && pwd)"
CONTEXT_SUBDIR="${CONTEXT_SUBDIR:-context}"
CONTEXT_DIR="${RUN_DIR_ABS}/${CONTEXT_SUBDIR}"
COMMAND_DIR="${CONTEXT_DIR}/commands"
mkdir -p "${COMMAND_DIR}"

SOURCE_CHECKOUT="${SOURCE_CHECKOUT:-${SOURCE_DIR:-$(pwd)}}"
STAMP="$(date -Iseconds 2>/dev/null || date)"

clean_value() {
    local value="$1"
    value="${value//$'\n'/ }"
    value="${value//|/\\|}"
    printf '%s' "${value}"
}

row() {
    local name="$1"
    local value="${!name-}"
    if [ -z "${value}" ]; then
        value="unknown"
    fi
    printf '| `%s` | `%s` |\n' "${name}" "$(clean_value "${value}")"
}

array_row() {
    local name="$1"
    local value=""
    local declaration=""
    declaration="$(declare -p "${name}" 2>/dev/null || true)"
    if [[ "${declaration}" == declare\ -a* || "${declaration}" == declare\ -A* ]]; then
        eval 'value="${'"${name}"'[*]}"'
    else
        value="${!name-}"
    fi
    if [ -z "${value}" ]; then
        value="unknown"
    fi
    printf '| `%s` | `%s` |\n' "${name}" "$(clean_value "${value}")"
}

write_vars() {
    local name
    for name in "$@"; do
        row "${name}"
    done
}

write_arrays() {
    local name
    for name in "$@"; do
        array_row "${name}"
    done
}

write_git_context() {
    local checkout="$1"
    {
        echo "# Git Context"
        echo
        echo "source_checkout=${checkout}"
        if [ ! -d "${checkout}" ]; then
            echo "source checkout not found"
            return 0
        fi
        git -C "${checkout}" -c safe.directory="${checkout}" rev-parse --show-toplevel
        git -C "${checkout}" -c safe.directory="${checkout}" rev-parse --abbrev-ref HEAD
        git -C "${checkout}" -c safe.directory="${checkout}" rev-parse HEAD
        echo
        echo "## Status"
        git -C "${checkout}" -c safe.directory="${checkout}" status --short --branch
        echo
        echo "## Remotes"
        git -C "${checkout}" -c safe.directory="${checkout}" remote -v
        echo
        echo "## Submodules"
        git -C "${checkout}" -c safe.directory="${checkout}" submodule status --recursive 2>/dev/null || true
    } > "${CONTEXT_DIR}/git.txt" 2>&1 || true
}

write_os_context() {
    {
        echo "# OS Context"
        echo "captured_at=${STAMP}"
        echo "hostname=$(hostname 2>/dev/null || true)"
        echo "user=$(id -un 2>/dev/null || true)"
        echo "uid_gid=$(id 2>/dev/null || true)"
        echo "pwd=$(pwd)"
        echo "uname=$(uname -a 2>/dev/null || true)"
        if [ -f /etc/os-release ]; then
            echo
            echo "## /etc/os-release"
            cat /etc/os-release
        fi
        if command -v lscpu >/dev/null 2>&1; then
            echo
            echo "## CPU"
            lscpu
        fi
    } > "${CONTEXT_DIR}/os.txt" 2>&1 || true
}

write_python_context() {
    local python_bin="${PYTHON_BIN:-python3}"
    {
        echo "# Python Runtime"
        echo "PYTHON_BIN=${python_bin}"
        command -v "${python_bin}" || true
        "${python_bin}" --version || true
        "${python_bin}" - <<'PY' || true
import importlib.metadata as metadata
import os
import platform
import sys

print(f"executable={sys.executable}")
print(f"platform={platform.platform()}")
print(f"prefix={sys.prefix}")
print(f"base_prefix={sys.base_prefix}")
print(f"CONDA_PREFIX={os.environ.get('CONDA_PREFIX', '')}")
print(f"VIRTUAL_ENV={os.environ.get('VIRTUAL_ENV', '')}")

packages = [
    "lmdeploy",
    "torch",
    "triton",
    "transformers",
    "accelerate",
    "sentencepiece",
    "protobuf",
    "openai",
    "httpx",
    "aiohttp",
    "vllm",
    "sglang",
]
for name in packages:
    try:
        version = metadata.version(name)
    except metadata.PackageNotFoundError:
        version = "not-installed"
    print(f"{name}={version}")

try:
    import torch

    print(f"torch.version.cuda={torch.version.cuda}")
    print(f"torch.cuda.is_available={torch.cuda.is_available()}")
    print(f"torch.cuda.device_count={torch.cuda.device_count()}")
except Exception as exc:
    print(f"torch_context_error={type(exc).__name__}: {exc}")
PY
    } > "${CONTEXT_DIR}/python.txt" 2>&1 || true
}

write_gpu_context() {
    {
        echo "# Accelerator Platform"
        if ! command -v nvidia-smi >/dev/null 2>&1; then
            echo "nvidia-smi not found"
            return 0
        fi
        nvidia-smi -L
        echo
        nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total,memory.used,utilization.gpu,power.draw,clocks.sm,clocks.mem --format=csv
        echo
        echo "## Topology"
        nvidia-smi topo -m 2>/dev/null || true
        echo
        echo "## Full nvidia-smi"
        nvidia-smi
    } > "${CONTEXT_DIR}/gpu.txt" 2>&1 || true
}

write_model_context() {
    {
        echo "# Model Context"
        write_vars MODEL_PATH MODEL_ABBR MODEL_LABEL TOKENIZER_PATH MODEL_DTYPE MODEL_WEIGHT_DTYPE
        local model_path="${MODEL_PATH:-}"
        if [ -n "${model_path}" ] && [ -d "${model_path}" ]; then
            echo
            echo "## Model Files"
            for name in config.json tokenizer_config.json generation_config.json preprocessor_config.json model_index.json; do
                if [ -f "${model_path}/${name}" ]; then
                    sha256sum "${model_path}/${name}"
                fi
            done
        elif [ -n "${model_path}" ]; then
            echo
            echo "MODEL_PATH is not a local directory: ${model_path}"
        fi
    } > "${CONTEXT_DIR}/model.txt" 2>&1 || true
}

write_filtered_env() {
    env | LC_ALL=C sort \
        | grep -E '^(ACC_|BACKEND|BENCH_|CONDA|CONTEXT_|CUDA|DATASET|DEPLOYMENT_|FEATURE_|HF_|HOST=|IMAGE_|INFRA_|LMDEPLOY|MODEL|NCCL|NVIDIA|OMP_|PORT=|PYTHON|SGLANG|SLO_|SOURCE_|TOKENIZERS_|TORCH|TRITON|VLLM|WORKLOAD_)=' \
        | grep -Ev '(API_KEY|KEY=|PASSWORD|SECRET|TOKEN=)' \
        > "${CONTEXT_DIR}/env.filtered" 2>/dev/null || true
}

write_command_readme() {
    cat > "${COMMAND_DIR}/README.md" <<'EOF'
# Commands

Store exact server and client command lines here. Benchmark helper scripts mirror
their `.cmd` files into this directory; for ad hoc commands, write one command
per `.cmd` file before execution.
EOF
}

write_deployment_context() {
    {
        echo "# Deployment Context"
        echo
        echo "Captured at: ${STAMP}"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        printf '| `%s` | `%s` |\n' "RUN_DIR" "$(clean_value "${RUN_DIR_ABS}")"
        printf '| `%s` | `%s` |\n' "SOURCE_CHECKOUT" "$(clean_value "${SOURCE_CHECKOUT}")"
        printf '| `%s` | `%s` |\n' "CONFIG_FILE" "$(clean_value "${CONFIG_FILE:-unknown}")"
        row HOSTNAME
        row CUDA_VISIBLE_DEVICES
        row CONDA_DEFAULT_ENV
        row CONDA_PREFIX
        row VIRTUAL_ENV
        echo
        echo "## Model"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        write_vars MODEL_PATH MODEL_ABBR MODEL_LABEL TOKENIZER_PATH MODEL_DTYPE MODEL_WEIGHT_DTYPE
        echo
        echo "## Serving Scenario"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        write_vars MODALITY DATASET_NAME DATASET_PATH DATASET_SPLIT WORKLOAD_PRESET ACCURACY_TASK NUM_SHOTS START_INDEX NUM_EXAMPLES NUM_THREADS TEMPERATURE TOP_P MAX_TOKENS REQUEST_RATE
        write_arrays OUT_LENS NUM_PROMPTS IMAGE_INPUT_LENS IMAGE_OUTPUT_LENS IMAGE_NUM_PROMPTS IMAGE_RESOLUTIONS IMAGE_COUNTS
        write_vars IMAGE_FORMAT IMAGE_CONTENT IMAGE_RANGE_RATIO EXTRA_BODY_JSON EXTRA_REQUEST_BODY
        echo
        echo "## SLO And Acceptance"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        write_vars SLO_MAX_MEAN_TTFT_MS SLO_MAX_MEAN_TPOT_MS SLO_MAX_MEAN_ITL_MS SLO_MAX_E2E_LATENCY_MS SLO_MIN_REQUEST_THROUGHPUT SLO_MIN_OUTPUT_THROUGHPUT SLO_MIN_SUCCESS_RATE SLO_MIN_ACCURACY
        echo
        echo "## Serving Topology And Parallelism"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        write_vars DEPLOYMENT_ARCHITECTURE SERVER_REPLICAS BACKEND API_BACKEND_LABEL IMAGE_API_BACKEND_LABEL HOST BENCH_HOST PORT TENSOR_PARALLEL_SIZE PIPELINE_PARALLEL_SIZE DATA_PARALLEL_SIZE EXPERT_PARALLEL_SIZE QUANT_POLICY KV_CACHE_DTYPE CACHE_MAX_ENTRY_COUNT
        echo
        echo "## Versioned Runtime Profile"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        write_vars RUNTIME_PROFILE_LABEL LMDEPLOY_BIN PYTHON_BIN PROFILE_RESTFUL_API CONTAINER_IMAGE CONTAINER_DIGEST CUDA_HOME NCCL_VERSION
        echo
        echo "## Accelerator Platform"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        write_vars NODE_NAME GPU_MODEL GPU_COUNT GPU_INTERCONNECT CUDA_VISIBLE_DEVICES NVIDIA_VISIBLE_DEVICES
        echo
        echo "## Captured Files"
        echo
        echo "- deployment_context.md: high-level deployment-space record"
        echo "- config.sh.snapshot: benchmark config at capture time, when provided"
        echo "- commands/: exact command lines"
        echo "- git.txt: source checkout branch, commit, remotes, status"
        echo "- python.txt: interpreter and package versions"
        echo "- gpu.txt: accelerator inventory and utilization snapshot"
        echo "- os.txt: host OS and CPU snapshot"
        echo "- env.filtered: relevant non-secret environment variables"
        echo "- model.txt: model identifiers and local config hashes when available"
    } > "${CONTEXT_DIR}/deployment_context.md"
}

export HOSTNAME="${HOSTNAME:-$(hostname 2>/dev/null || true)}"

if [ -n "${CONFIG_FILE}" ]; then
    cp "${CONFIG_FILE}" "${CONTEXT_DIR}/config.sh.snapshot"
fi

write_command_readme
write_deployment_context
write_git_context "${SOURCE_CHECKOUT}"
write_os_context
write_python_context
write_gpu_context
write_model_context
write_filtered_env

echo "context_dir=${CONTEXT_DIR}"
