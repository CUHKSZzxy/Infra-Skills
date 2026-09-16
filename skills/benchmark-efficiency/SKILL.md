---
name: benchmark-efficiency
description: Use when measuring LMDeploy serving throughput, latency, or capacity without a profiler.
---

# Benchmark Efficiency

Use `profile-serving-timeline` for short LMDeploy, vLLM, or SGLang traces,
`optimize-kernel` after a kernel hotspot is known, and `benchmark-accuracy` for
dataset correctness.

## Client Selection

- Use the bundled client for ShareGPT, random, or image/text benchmarks.
- For EvalScope `perf`, including live or prebuilt SWE-Smith multi-turn workloads,
  follow [EvalScope benchmarking](references/evalscope.md).
- For InferenceX agentic trace replay, use the AgentX Harness fork of AIPerf;
  follow [InferenceX benchmarking](references/inferencex.md).

Preserve a user-supplied client's workload semantics. Do not replace it with a
custom request loop or silently change dataset construction, warmup, or cache
busting. Compare server variants within the same client and workload; results
from different harnesses are not directly interchangeable.

## Measurement Contract

Use [artifact conventions](../../docs/conventions/benchmark-artifacts.md) for
the run directory and logs, honoring a user-provided destination. Capture
[deployment context](../../docs/conventions/deployment-context.md) before the
run with `scripts/capture_context.sh`. Fill only benchmark-critical gaps;
leave unavailable facts as `unknown` or `null`.

- For comparisons, run baseline/candidate on the same workload with recorded
  source snapshots. Keep weight and KV-cache quantization labels distinct.
  Measure isolated/cumulative variants when attribution across changes matters.
- Record length policy, prompt count, rate/concurrency, streaming, ignore-EOS,
  seed, SLO, warmup/trial counts, and multimodal image count/resolution/content.
  Include a default/disabled or high-limit variant when admission, queue, or
  flow-control limits might cap throughput.
- For steady-state measurements, warm the exact measured batch size, graph key,
  and feature path before timing; smaller warmups may leave lazy setup in the
  first sample. For an explicitly cold-cache or no-client-warmup workload,
  preserve that policy, restart each server variant, and label the result.
  Engine initialization still runs; a fresh server does not clear external KV
  stores. Record their reset/isolation policy when present.
- Record GPU memory, utilization, power, and clocks per variant. Reject
  contamination from other processes. If a sweep rotates jobs across GPUs,
  wait for its controller rather than relying on a momentarily idle sample.
- For optimization claims, use at least three trials under the same declared
  warmup/cache policy and report variance. Alternate baseline/candidate order.
  Deltas below roughly 3-5% need measured low variance.
  Include boundary/small loads for shape-dependent dispatch.
- Truncated checkpoints do not establish speculative-decoding throughput when
  acceptance is unrepresentative. Disable MTP for that comparison or report
  acceptance separately.

Save exact commands under `context/commands/` before running; bundled helpers do
this automatically. Keep server/client logs in the run folder with labels for
model, parallelism, feature, dataset, output length, and prompt count. Use
`collect_bench.py` for bundled-client comparison CSVs; use the native exports
in the references for EvalScope and InferenceX. Report failed or skipped
variants too.
If performance regresses, use the observed startup, queue, prefill, or decode
signal to choose the next focused investigation.

## Bundled Scripts

Use `scripts/lmdeploy_config.sh` as the run-local configuration template.
Resolve script paths from `INFRA_SKILLS_HOME` in
[machine conventions](../../docs/conventions/machines.md).

- `capture_context.sh`: deployment metadata and command directory.
- `lmdeploy_serve.sh`: labeled server logs and saved launch command. Set
  `SERVE_BACKGROUND=1` when the same shell needs to launch clients afterward.
- `wait_server.sh`: readiness polling with localhost proxies disabled.
- `bench_sharegpt.sh` / `bench_image.sh`: text or synthetic image/text matrix;
  the latter sends OpenAI chat-compatible multimodal requests.
- `profile_restful_api.py`: bundled client for `sharegpt`, `random`, and `image`.
- `api_smoke.py`: deterministic response samples when output checks are relevant.
- `collect_bench.py`: logs to comparison CSVs and plots.

Set model, topology, quantization, and SLO in the copied config. ShareGPT runs
need `DATASET_PATH`. For a new synthetic multimodal setup,
`IMAGE_WORKLOAD_PRESET=quick` is a small stability probe; choose the actual
measurement preset for the task. `BENCH_STREAM_LOGS=0` reduces output for large
matrices; normal redirected serve logs usually suffice.

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

## Result

Write `summary.md` with measurement tables (baseline/candidate for comparisons),
configuration, workload, commands, artifact paths, errors, fixes, and caveats.
For optimization comparisons, include variance and failed/skipped/SLA-failing
variants. State when admission/concurrency limits cap throughput. Check response
parity or shape when the change could affect output. Distinguish API measurements
from profiler/kernel evidence.
Include the run folder, summary path, and `context/deployment_context.md` path
in the final response, following artifact conventions.
