---
name: llm-e2e-benchmark
description: Use when benchmarking end-to-end LLM serving performance or accuracy across LMDeploy/vLLM/SGLang, especially when comparing feature flags such as FP8 KV cache, quant policy, backend, TP/DP, or long-context throughput.
---

# LLM End-To-End Benchmark

Use this when the question is user-visible serving behavior: throughput, TTFT,
TPOT/ITL, memory capacity, output quality, or accuracy under a real API/server
flow. Pair with `triton-kernel-performance` only after the slow stage is known
to be a kernel.

## Workflow

1. Record the exact matrix before running:
   - repo/commit, package import path, Python env,
   - model path and model alias,
   - backend, TP/DP/EP, quant policy or KV-cache dtype,
   - dataset, prompt count, input/output length policy,
   - GPU/node placement and server extra args.
2. Run one baseline and one candidate with the same workload. For KV-cache work,
   keep weight quantization separate from KV-cache quantization in labels.
3. Keep serving logs and benchmark logs under the same run directory. The log
   filename must encode model, parallelism, feature label, dataset, output
   length, and prompt count.
4. Summarize logs into CSV before drawing conclusions. Treat under 3-5%
   throughput deltas as noise unless reruns show lower variance.
5. If end-to-end performance regresses, split the problem:
   - server startup/model load,
   - prefill throughput and TTFT,
   - decode throughput and TPOT/ITL,
   - request scheduling/concurrency,
   - kernel-level cache fill/decode/attention.

## Bundled Scripts

Copy or invoke the scripts from `scripts/`:

- `lmdeploy_config.sh`: editable benchmark config template.
- `lmdeploy_serve.sh`: start an LMDeploy OpenAI-compatible server with stable
  labels and logs.
- `wait_server.sh`: poll `/v1/models` with proxy disabled for localhost.
- `bench_sharegpt.sh`: run a ShareGPT-style API benchmark matrix.
- `profile_restful_api.py`: bundled OpenAI-compatible benchmark client copied
  from the local LMDeploy benchmark flow.
- `api_smoke.py`: save deterministic OpenAI-compatible responses for quick
  baseline/candidate quality checks.
- `collect_bench.py`: parse benchmark logs into CSV and comparison plots.

Typical layout:

```bash
cp skills/llm-e2e-benchmark/scripts/lmdeploy_config.sh ./config.sh
# edit MODEL_PATH, MODEL_ABBR, TP, BACKEND, QUANT_POLICY
source ./config.sh

bash skills/llm-e2e-benchmark/scripts/lmdeploy_serve.sh ./config.sh baseline
bash skills/llm-e2e-benchmark/scripts/wait_server.sh ./config.sh
python skills/llm-e2e-benchmark/scripts/api_smoke.py \
  --base-url http://127.0.0.1:23334/v1 --model "$MODEL_ABBR" \
  --out ./analysis/baseline_smoke.jsonl
bash skills/llm-e2e-benchmark/scripts/bench_sharegpt.sh ./config.sh baseline

python skills/llm-e2e-benchmark/scripts/collect_bench.py \
  --log-dir ./0_bench_logs --out-dir ./analysis \
  --baseline-group baseline --candidate-group kvfp8 \
  --baseline-label "BF16 KV" --candidate-label "FP8 KV"
```

Local defaults on this machine:

- ShareGPT dataset: `/nvme1/shared/ShareGPT_V3_unfiltered_cleaned_split.json`
- Benchmark client: `scripts/profile_restful_api.py`
- Fast matrix: `OUT_LENS=(None 2048)` and
  `NUM_PROMPTS=(1000 1000)`
- Medium matrix: `OUT_LENS=(None 2048 4096 8192)` and
  `NUM_PROMPTS=(1000 1000 500 200)`
- Full matrix: `OUT_LENS=(None 2048 4096 8192 16384 32768)` and
  `NUM_PROMPTS=(10000 8000 8000 4000 1000 500)`

Use `WORKLOAD_PRESET=fast` for agent smoke benchmarks, `medium` for a more
useful development comparison, and `full` only when the server is stable and
the comparison is worth the runtime.

Do not add `--log-level` by default. Normal LMDeploy serve logging is useful
and stays on disk because `SERVE_STREAM_LOGS=0` redirects stdout/stderr to the
serve log. Add `--log-level INFO` in `LMDEPLOY_EXTRA_ARGS` only when debugging
serve details. Use `SERVE_BACKGROUND=1` when a script should start the server
and return after writing a pid file beside the serve log.
Keep `BENCH_STREAM_LOGS=0` for larger benchmark matrices; the script still
prints the per-case log path before redirecting benchmark output.

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

Before reporting a win, provide:

- exact serve and benchmark commands,
- summary CSV or table with baseline and candidate,
- one short quality/accuracy smoke if changing quantization behavior,
- whether the run measured only API macrobenchmarks or also kernel/profiler
  evidence.
