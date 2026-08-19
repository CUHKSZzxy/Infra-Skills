---
name: benchmark-efficiency
description: Use when measuring profiler-free LMDeploy API or server efficiency, including throughput, TTFT, TPOT/ITL, memory capacity, concurrency, KV-cache settings, or feature comparisons; use profile-serving-timeline for trace diagnosis and optimize-kernel for isolated kernels.
---

# Benchmark Efficiency

Use `profile-serving-timeline` for short LMDeploy, vLLM, or SGLang traces,
`optimize-kernel` after a kernel hotspot is known, and `benchmark-accuracy` for
dataset correctness.

## Workflow

1. Create the run folder under the current source checkout's `benchmark/`
   directory. Follow `../../docs/local-conventions.md` for naming, summary, and
   artifact subfolder layout. If the user names a desired destination or run
   folder, put the benchmark folder there and state that path before long runs.
2. Record the exact matrix before running:
   - repo/commit, package import path, Python env,
   - model path and model alias,
   - backend, TP/DP/EP, quant policy or KV-cache dtype,
   - dataset, prompt count, input/output length policy,
   - GPU/node placement and server extra args.
3. Run baseline and candidate with the same workload. Keep weight quantization
   separate from KV-cache quantization in labels. For admission, queue, or
   multimodal flow-control knobs, include a disabled/default or high-limit
   variant so the limit itself is not the throughput cap. For multiple
   independent changes, predefine Baseline, isolated variants, and cumulative
   variants using immutable source snapshots.
4. Warm the exact measured batch size, CUDA-graph key, and feature branch
   before trial 1. A small warmup may not initialize the graph or lazy path used
   by a large-batch measurement.
5. Keep serving logs and benchmark logs under the same run directory. The log
   filename must encode model, parallelism, feature label, dataset, output
   length, and prompt count.
6. Record GPU memory, utilization, power, and clocks beside every variant.
   Reject a run when another process changes occupancy or clocks. If an
   external sweep rotates jobs across devices, wait for its controller to exit
   rather than trusting a transient idle sample.
7. Summarize logs into CSV before drawing conclusions. Use at least three
   post-warmup trials and report variance for optimization claims. Treat under
   3-5% throughput deltas as noise unless reruns show lower variance.
   For shape- or threshold-dependent dispatch, measure the target load and at
   least one small or boundary case instead of extrapolating one shape.
8. If end-to-end performance regresses, split the problem:
   - server startup/model load,
   - prefill throughput and TTFT,
   - decode throughput and TPOT/ITL,
   - request scheduling/concurrency,
   - kernel-level cache fill/decode/attention.
9. Truncated checkpoints are useful for kernel and control-flow comparisons,
   but not for speculative-decoding throughput when their acceptance is
   unrepresentative. Disable MTP for the main efficiency comparison or report
   acceptance separately; do not attribute rejected-draft overhead to the
   optimization under test.
10. Write `summary.md` with config, workload, commands, metric tables, artifact
   paths, server errors, fixes, caveats, and failed/skipped variants. Final
   responses must include the run folder and exact `summary.md` path.

## Bundled Scripts

Copy or invoke the scripts from `scripts/`:

- `lmdeploy_config.sh`: editable benchmark config template.
- `lmdeploy_serve.sh`: start an LMDeploy OpenAI-compatible server with stable
  labels and logs.
- `wait_server.sh`: poll `/v1/models` with proxy disabled for localhost.
- `bench_sharegpt.sh`: run a ShareGPT-style API benchmark matrix.
- `bench_image.sh`: run a synthetic image+text API benchmark matrix through
  OpenAI chat-compatible multimodal requests.
- `profile_restful_api.py`: bundled OpenAI-compatible benchmark client; the
  config template points to this copy by absolute local path. It supports
  `sharegpt`, `random`, and `image` datasets.
- `api_smoke.py`: save deterministic OpenAI-compatible responses for quick
  baseline/candidate response-shape checks.
- `collect_bench.py`: parse benchmark logs into CSV and comparison plots.

Load `references/result-schema.md` when a local LMDeploy run needs normalized
JSONL rows or failed-candidate reporting beyond the baseline/candidate CSV
helpers.

Typical layout:

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/local-conventions.md}"
SKILL_DIR="$INFRA_SKILLS_HOME/skills/benchmark-efficiency"
MODEL_LABEL=qwen35_35b
RUN_DATE=${RUN_DATE:-$(date +%Y%m%d)}
RUN_DIR="./benchmark/${RUN_DATE}_${MODEL_LABEL}_sharegpt_kvfp8"
mkdir -p "$RUN_DIR"
cp "$SKILL_DIR/scripts/lmdeploy_config.sh" "$RUN_DIR/config.sh"
cd "$RUN_DIR"
# edit MODEL_PATH, MODEL_ABBR, TP, BACKEND, QUANT_POLICY
source ./config.sh
mkdir -p ./analysis

bash "$SKILL_DIR/scripts/lmdeploy_serve.sh" ./config.sh baseline
bash "$SKILL_DIR/scripts/wait_server.sh" ./config.sh
python "$SKILL_DIR/scripts/api_smoke.py" \
  --base-url http://127.0.0.1:23334/v1 --model "$MODEL_ABBR" \
  --out ./analysis/baseline_response_check.jsonl
bash "$SKILL_DIR/scripts/bench_sharegpt.sh" ./config.sh baseline

python "$SKILL_DIR/scripts/collect_bench.py" \
  --log-dir ./bench_logs --out-dir ./analysis \
  --baseline-group baseline --candidate-group kvfp8 \
  --baseline-label "BF16 KV" --candidate-label "FP8 KV"
```

Image quick-check layout:

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/local-conventions.md}"
SKILL_DIR="$INFRA_SKILLS_HOME/skills/benchmark-efficiency"
MODEL_LABEL=qwen35_35b_a3b
RUN_DATE=${RUN_DATE:-$(date +%Y%m%d)}
RUN_DIR="./benchmark/${RUN_DATE}_${MODEL_LABEL}_image_quick"
mkdir -p "$RUN_DIR"
cp "$SKILL_DIR/scripts/lmdeploy_config.sh" "$RUN_DIR/config.sh"
cd "$RUN_DIR"
# edit MODEL_PATH, MODEL_ABBR, TP, BACKEND, QUANT_POLICY, PORT
source ./config.sh

bash "$SKILL_DIR/scripts/lmdeploy_serve.sh" ./config.sh baseline
bash "$SKILL_DIR/scripts/wait_server.sh" ./config.sh
bash "$SKILL_DIR/scripts/bench_image.sh" ./config.sh baseline
```

Local defaults on this machine:

- ShareGPT dataset: set `DATASET_PATH` in the copied config; no machine-local
  dataset path is assumed.
- Benchmark client:
  `$INFRA_SKILLS_HOME/skills/benchmark-efficiency/scripts/profile_restful_api.py`

| Preset | OUT_LENS | NUM_PROMPTS | Use |
| --- | --- | --- | --- |
| `fast` | `None 2048` | `1000 1000` | quick agent benchmark |
| `medium` | `None 2048 4096 8192` | `1000 1000 500 200` | development comparison |
| `full` | `None 2048 4096 8192 16384 32768` | `10000 8000 8000 4000 1000 500` | stable server, worthwhile runtime |

For image benchmarks, use `IMAGE_WORKLOAD_PRESET=quick` for a first agent check:
`IMAGE_INPUT_LENS=(100)`, `IMAGE_OUTPUT_LENS=(100)`,
`IMAGE_NUM_PROMPTS=(10)`, `IMAGE_RESOLUTIONS=(1024x1024)`, and
`IMAGE_COUNTS=(1)`. The image wrapper defaults to
`IMAGE_API_BACKEND_LABEL=lmdeploy-chat` and does not require `DATASET_PATH`,
because it generates synthetic `image_url` data URIs in the benchmark client.
Use `IMAGE_WORKLOAD_PRESET=fast` only after the server is stable.

Do not add `--log-level` by default; redirected normal serve logs are usually
enough. Use `SERVE_BACKGROUND=1` for non-blocking server launch and keep
`BENCH_STREAM_LOGS=0` for larger matrices.

For LMDeploy KV-cache quant labels:

- `QUANT_POLICY=0`: no KV-cache quantization.
- `QUANT_POLICY=fp8` or branch-specific numeric policy: FP8 KV cache if the
  checkout supports that CLI value.
- Keep exact quant labels for variants, such as `fp8` vs `fp8_e5m2`. The
  collector preserves `kvfp8_e5m2` as a distinct group, so compare it with
  `--candidate-group kvfp8_e5m2` rather than folding it into `kvfp8`.

Keep model weight dtype in `MODEL_ABBR`. Use `FEATURE_LABEL` for non-KV
feature toggles; the scripts encode it as `feature-<label>` so the collector
can group it.

## Acceptance

Before reporting a win, provide the exact serve/benchmark commands, baseline
and candidate table, failed/skipped/SLA-failing variants, output parity or a
response-shape check when relevant, API-only versus profiler/kernel evidence,
and proof that admission/concurrency limits did not cap throughput.
