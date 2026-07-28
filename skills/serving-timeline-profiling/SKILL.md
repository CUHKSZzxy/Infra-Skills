---
name: serving-timeline-profiling
description: Use when capturing or comparing short PyTorch/CUDA serving timelines for LMDeploy or vLLM, identifying inference bottlenecks, checking multi-GPU rank balance, or re-profiling an optimization before an unprofiled throughput benchmark.
---

# Serving Timeline Profiling

Use this skill for trace-based diagnosis. Use `e2e-efficiency-benchmark` for the
separate, profiler-free throughput/latency measurement that follows.

## Workflow

1. Define the phase and comparison before launching:
   - prefill, steady decode, or mixed traffic;
   - one baseline or baseline/candidate;
   - request count, prompt, forced output length, and capture duration.
2. Record invariants: exact checkpoint, repo/image commit, import path, GPUs,
   TP/DP/EP, graph/eager mode, quantization, kernel backends, memory settings,
   and every non-default serve flag. Compare one intentional change at a time.
3. Create `benchmark/e2e_<model>_<system>_profile[_<feature>]/` under the
   measured checkout, following `../../docs/local-conventions.md`. Keep
   `0_profiles/`, `0_profile_workload/`, `0_serve_logs/`, `0_analysis/`, and a
   root `summary.md`.
4. Read only the serving-system reference needed for launch:
   - LMDeploy: [references/lmdeploy.md](references/lmdeploy.md)
   - vLLM: [references/vllm.md](references/vllm.md)
   Read both when comparing the systems.
5. Prove the same command works once without the profiler. Warm model loading,
   JIT/autotuning, CUDA-graph capture, and library shape caches before the
   measured window. Warm the exact measured batch/graph key and runtime branch;
   a smaller warmup can leave lazy graph capture or feature-specific setup in
   the first sample. Do not enable eager mode or skip DeepGEMM/library warmup
   merely to simplify profiling; those change the workload being diagnosed.
6. Drive a small, deterministic workload. For steady decode, use a few
   concurrent long requests with `ignore_eos=true`, wait until every request is
   running and tokens are advancing, then capture only 0.5-2 seconds. Account
   for client tokenizer/dataset setup when using timer-based profilers; their
   delay is not necessarily tied to the first request. For prefill, start
   capture immediately before submitting requests.
7. Stop and flush the profiler before cancelling clients or killing the
   server. Trace flushing can take much longer than capture. Validate every TP
   rank file parses, contains the intended annotation and enough complete
   cycles for the intended analysis, and exercises the expected kernel branch;
   steady-state decode normally requires multiple cycles. File existence or
   size is insufficient. Use fresh output labels so stale traces cannot satisfy
   the harness. Then stop clients/server and verify no matching process,
   container, or GPU compute process remains.
8. Analyze and re-profile the candidate with the identical payload. After the
   timeline explains the change, run a separate profiler-free benchmark with
   `e2e-efficiency-benchmark`.
9. Monitor GPU memory, utilization, power, and clocks during each capture.
   Reject runs contaminated by another process or a one-rank collective stall.
   If an external sweep rotates work across GPUs, wait for its controller to
   exit instead of racing a momentarily idle sample.

## Analyze Traces

Start with the bundled dependency-free summarizer:

```bash
INFRA_SKILLS_HOME=${INFRA_SKILLS_HOME:-/home/zhouxinyu/common/Infra-Skills}
ANALYZER="$INFRA_SKILLS_HOME/skills/serving-timeline-profiling/scripts/summarize_torch_trace.py"

python "$ANALYZER" \
  --step-regex 'forward_cudagraph' \
  ./benchmark/e2e_<run>/0_profiles/lmdeploy_rank*.json.gz

python "$ANALYZER" \
  --step-regex 'execute_context_.*generation' \
  ./benchmark/e2e_<run>/0_profiles/*.pt.trace.json.gz
```

Use repeated `--group NAME=REGEX` arguments for strict, auditable kernel
families. Keep broad semantic groupings separate from exact-name comparisons.
The first matching group owns each kernel.

Interpret results in this order:

1. Median GPU forward range and consecutive start-to-start cycle interval.
2. Stable cross-rank spread, excluding profiler-boundary and obviously
   truncated collective events.
3. Kernel families, their call counts, and graph-child versus outside-graph
   launches.
4. CPU submission only after checking whether apparent synchronization belongs
   to a background GPU-wait thread.

Summed kernel duration may exceed wall time when streams overlap. A single host
CUDA-graph launch can contain thousands of child kernels. Label reciprocal
cycle rate as timeline-implied cadence, never benchmark throughput.
Inspect median, mean, p95, and max together. If one rank has an
orders-of-magnitude outlier while the other ranks are stable, recapture rather
than hiding it in a rank-average.

## Acceptance

Write `summary.md` with:

- exact launch and workload commands;
- capture phase, duration, active/waiting request evidence, and trace count;
- median forward/cycle timing and cross-rank spread;
- top strict kernel families with explicit category boundaries;
- baseline/candidate deltas and remaining bottlenecks;
- profiler perturbation and cross-system comparability caveats;
- excluded or recaptured traces with concrete reasons;
- server/client/GPU cleanup status;
- the planned or completed profiler-free benchmark.

Retain commands, payloads, timestamps, metrics snapshots, traces, analyzer
output, and successful logs. Remove only disposable compile/autotune caches
after confirming they are not needed for another controlled launch.
