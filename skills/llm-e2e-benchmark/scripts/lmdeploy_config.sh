#!/usr/bin/env bash
# Shared config for LMDeploy end-to-end benchmark scripts.
# Copy this file near your experiment and edit the values below.

# Model and server identity.
MODEL_PATH="/path/to/model"
MODEL_ABBR="model_abbr"
BACKEND="pytorch"
HOST="0.0.0.0"
BENCH_HOST="127.0.0.1"
PORT=23334
LMDEPLOY_BIN="${LMDEPLOY_BIN:-lmdeploy}"

# Parallelism. DATA_PARALLEL_SIZE is included in labels for experiments that
# launch multiple server replicas externally; lmdeploy_serve.sh only passes TP.
TENSOR_PARALLEL_SIZE=1
DATA_PARALLEL_SIZE=1

# KV-cache quantization policy for LMDeploy.
# Use 0 for no KV-cache quantization. Branches may also accept names such as fp8.
QUANT_POLICY="0"

# Extra labels and args. Keep this empty by default; logs are redirected to
# files by the runner. Add --log-level INFO only when debugging serve details.
FEATURE_LABEL=""
LMDEPLOY_EXTRA_ARGS=()
SERVE_BACKGROUND="${SERVE_BACKGROUND:-0}"
SERVE_STREAM_LOGS="${SERVE_STREAM_LOGS:-0}"

# Benchmark client.
PYTHON_BIN="${PYTHON_BIN:-python3}"
PROFILE_RESTFUL_API="/nvme1/zhouxinyu/Infra-Skills/skills/llm-e2e-benchmark/scripts/profile_restful_api.py"
API_BACKEND_LABEL="lmdeploy"
DATASET_NAME="sharegpt"
DATASET_PATH="/nvme1/shared/ShareGPT_V3_unfiltered_cleaned_split.json"
BENCH_EXTRA_ARGS=()
BENCH_STREAM_LOGS="${BENCH_STREAM_LOGS:-0}"

# Workload presets. Use custom only after setting OUT_LENS and NUM_PROMPTS.
WORKLOAD_PRESET="${WORKLOAD_PRESET:-fast}"  # fast, medium, full, custom
case "${WORKLOAD_PRESET}" in
    fast)
        OUT_LENS=(None 2048)
        NUM_PROMPTS=(1000 1000)
        ;;
    medium)
        OUT_LENS=(None 2048 4096 8192)
        NUM_PROMPTS=(1000 1000 500 200)
        ;;
    full)
        OUT_LENS=(None 2048 4096 8192 16384 32768)
        NUM_PROMPTS=(10000 8000 8000 4000 1000 500)
        ;;
    custom)
        : "${OUT_LENS:?set OUT_LENS for WORKLOAD_PRESET=custom}"
        : "${NUM_PROMPTS:?set NUM_PROMPTS for WORKLOAD_PRESET=custom}"
        ;;
    *)
        echo "Unknown WORKLOAD_PRESET: ${WORKLOAD_PRESET}" >&2
        return 1 2>/dev/null || exit 1
        ;;
esac

# Logs are created relative to the directory containing this config file.
SERVE_LOG_DIR="0_serve_logs"
BENCH_LOG_DIR="0_bench_logs"
