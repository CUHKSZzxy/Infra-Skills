# SGLang PyTorch timeline

Use SGLang's HTTP profile controls or `sglang.benchmark.serving --profile` for
short PyTorch Chrome traces. The canonical upstream page is
<https://docs.sglang.io/docs/developer_guide/benchmark_and_profiling>.

## Launch

Start from the real serving command. On the shared-storage machine, use the
`sglang-dev` env and keep SGLang caches under the workspace so imports and JIT
builds do not try read-only home paths:

```bash
WORKSPACE_ROOT=${WORKSPACE_ROOT:-/mnt/shared-storage-user/zhouxinyu1}
SGLANG_DEV_SOURCE=${SGLANG_DEV_SOURCE:-$WORKSPACE_ROOT/sglang_dev}
CONDA_ROOT=${CONDA_ROOT:-$WORKSPACE_ROOT/miniconda3}

RUN_DIR=/absolute/path/to/benchmark/YYYYMMDD_model_sglang_profile
MODEL_PATH=/absolute/path/to/model
mkdir -p "$RUN_DIR/profiles" "$RUN_DIR/profile_workload" \
  "$RUN_DIR/serve_logs" "$RUN_DIR/analysis"

export SGLANG_CACHE_DIR=${SGLANG_CACHE_DIR:-$WORKSPACE_ROOT/.cache/sglang}
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$WORKSPACE_ROOT/.cache}
export SGLANG_TORCH_PROFILER_DIR="$RUN_DIR/profiles"
export PYTHONPATH="$SGLANG_DEV_SOURCE/python"

CUDA_VISIBLE_DEVICES=0,1 "$CONDA_ROOT/envs/sglang-dev/bin/python" \
  -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --tp-size 2 \
  --host 127.0.0.1 \
  --port 18039 \
  --trust-remote-code
```

`python -m sglang.launch_server` may warn that `sglang serve` is preferred; use
the module form when the env's console scripts are not on `PATH`. If custom
all-reduce JIT compilation fails and that path is not under test, relaunch with
`--disable-custom-all-reduce` instead of spending time on repeated fallback
warnings.

If a sandboxed client cannot reach a server launched outside the sandbox, run
the readiness probe and profile client in the same execution mode as the
server. Verify with `/health`, `/model_info`, and `/v1/models` before profiling.

## Capture

Use `sglang.benchmark.serving --profile` when its dataset and tokenizer setup is
already local and fast:

```bash
"$CONDA_ROOT/envs/sglang-dev/bin/python" -m sglang.benchmark.serving \
  --backend sglang \
  --host 127.0.0.1 \
  --port 18039 \
  --model "$MODEL_PATH" \
  --dataset-name random-ids \
  --random-input-len 128 \
  --random-output-len 96 \
  --num-prompts 16 \
  --max-concurrency 4 \
  --request-rate inf \
  --profile \
  --profile-activities CPU GPU \
  --profile-start-step 2 \
  --profile-num-steps 8 \
  --profile-output-dir "$RUN_DIR/profiles" \
  --profile-prefix sglang_smoke
```

Run the same benchmark once without `--profile` first if it may download
datasets, initialize tokenizers, or prepare prompts. In a local Qwen3.5 TP=2
smoke, `--dataset-name random` tried to download an HF fixture before sending
`/start_profile`, so no trace would have been captured until that setup
finished. Prefer `random-ids`, an explicit local dataset, or a small scripted
native `/generate` workload for short diagnostic profiles.

For the most deterministic window, call the HTTP endpoints directly from a
script that has already built its payloads:

```bash
curl --fail-with-body -X POST http://127.0.0.1:18039/start_profile \
  -H 'Content-Type: application/json' \
  -d '{
    "output_dir": "'"$RUN_DIR"'/profiles/http",
    "activities": ["CPU", "GPU"],
    "profile_prefix": "sglang_http",
    "detailed_annotations": true
  }'

# Immediately submit concurrent /generate requests with ignore_eos=true.

curl --fail-with-body --max-time 600 \
  -X POST http://127.0.0.1:18039/stop_profile
```

When `num_steps` is omitted, `/stop_profile` is required and waits for flushing.
When `num_steps` is set, SGLang auto-stops after that many forward steps; use
`start_step` to skip warmup iterations. Set `merge_profiles=true` only when all
ranks can write to shared storage and a merged trace is useful.

Use `detailed_annotations=true` for roofline-style per-step metadata. SGLang
then augments GPU `step[...]` annotations with phase-prefixed fields such as
`c_sq`, `c_sqsq`, `c_sqsk`, `c_sk` for context/prefill and `g_sq`, `g_sqsq`,
`g_sqsk`, `g_sk` for generation/decode. These annotations are visible in both
eager and CUDA-graph modes.

To profile CUDA-graph capture itself rather than steady runtime, launch with
`--enable-profile-cuda-graph` and opt into trace files with either
`SGLANG_ENABLE_CUDA_GRAPH_CAPTURE_TRACE=1` for one trace per TP rank or
`SGLANG_GRAPH_BATCH_CAPTURE=1` for one trace per captured batch size and rank.
Those traces are written under
`$SGLANG_TORCH_PROFILER_DIR/graph_capture_profile/`.

## Validation and pitfalls

- Expect one `{profile_prefix}-{profile_id}-TP-{rank}.trace.json.gz` file per
  TP rank, or additionally `merged-{profile_id}.trace.json.gz` when merging is
  enabled. Validate rank count against TP/DP/PP/EP settings.
- Check gzip integrity, file size, parseability, and trace contents. A tiny
  file or a trace without `step[...]` annotations is invalid for timeline
  diagnosis even if it is nonempty.
- Analyze steady serving traces with `--step-regex 'step\['`. With
  `detailed_annotations=true`, require expected `EXTEND`, `DECODE`, or `MIXED`
  step names and the relevant `c_`/`g_` aggregate fields.
- Record `/start_profile`, client-submit, response, `/stop_profile`, and trace
  dump timestamps. SGLang can flush for much longer than the request window.
- Preserve real graph/eager and backend flags unless the profile is explicitly
  about startup or graph capture. Do not add `--disable-cuda-graph` merely to
  make Python stacks easier unless that is the intended variant.
- If PyTorch profiler raises the known Python replay stack assertion, retry
  with `SGLANG_PROFILE_WITH_STACK=False` before changing the workload.
- Do not use trace-implied cycle rate as final throughput evidence; follow with
  a profiler-free benchmark when the trace explains the bottleneck.
