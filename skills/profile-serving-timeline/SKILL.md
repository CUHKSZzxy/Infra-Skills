---
name: profile-serving-timeline
description: Use when capturing or comparing short LMDeploy, vLLM, or SGLang PyTorch/CUDA serving traces to diagnose prefill/decode bottlenecks or rank imbalance; do not use trace-implied cadence as final throughput evidence.
---

# Profile Serving Timeline

Use this skill for trace-based diagnosis. Use `benchmark-efficiency` for the
separate, profiler-free throughput/latency measurement that follows.

## Workflow

1. Define the phase and comparison before launching:
   - prefill, steady decode, or mixed traffic;
   - one baseline or baseline/candidate;
   - request count, prompt, forced output length, capture delay, capture
     duration, and how the client will submit requests without human or agent
     think-time entering the capture window.
2. Record invariants: exact checkpoint, repo/image commit, import path, GPUs,
   TP/DP/EP, graph/eager mode, quantization, kernel backends, memory settings,
   and every non-default serve flag. Compare one intentional change at a time.
3. Create `benchmark/<YYYYMMDD>_<model>_<system>_profile[_<feature>]/`
   under the measured checkout, following `../../docs/local-conventions.md`.
   Keep `profiles/`, `profile_workload/`, `serve_logs/`, `analysis/`, and a root
   `summary.md`.
4. Read only the serving-system reference needed for launch:
   - LMDeploy: [references/lmdeploy.md](references/lmdeploy.md)
   - vLLM: [references/vllm.md](references/vllm.md)
   - SGLang: [references/sglang.md](references/sglang.md)
   Read each relevant reference when comparing systems.
5. Prove the same command works once without the profiler. Warm model loading,
   JIT/autotuning, CUDA-graph capture, and library shape caches before the
   measured window. Warm the exact measured batch/graph key and runtime branch;
   a smaller warmup can leave lazy graph capture or feature-specific setup in
   the first sample. Do not enable eager mode or skip DeepGEMM/library warmup
   merely to simplify profiling; those change the workload being diagnosed.
6. Drive a small deterministic workload from a script, never by typing a
   request after arming the profiler. For steady decode, submit a few long
   concurrent `ignore_eos=true` requests, wait until all are running and tokens
   advance, then capture about 5 seconds. Use 1 second only after a dry run
   proves requests are already active; extend toward 10 seconds only when
   timestamps show slow client startup, retries, or scheduler jitter. Account
   for agent delay, tokenizer/dataset setup, shell startup, and health-check
   retries. An unreasonably small trace, such as only a few KB, or an
   annotation-empty trace usually means no request work hit the capture window.
   For prefill, script the client immediately before the capture window or set
   delay/duration from measured client-submit timestamps.
7. Stop and flush the profiler before cancelling clients or killing the server.
   Validate every TP rank file parses, contains the intended annotation, has
   enough complete cycles, and exercises the expected kernel branch. File
   existence and nonzero size are insufficient. Recapture with a fresh prefix,
   scripted client, and wider or better-aligned window when traces are too
   small, annotation-empty, idle-only, or setup-only. Then stop clients/server
   and verify no matching process, container, or GPU compute process remains.
8. Analyze and re-profile the candidate with the identical payload. After the
   timeline explains the change, run a separate profiler-free benchmark with
   `benchmark-efficiency`. If it isolates one hot kernel but not the GPU-side
   limiting resource, switch to `optimize-kernel` for its optional NCU evidence
   gate; do not collect NCU counters across the full serving trace.
9. Monitor GPU memory, utilization, power, and clocks during each capture.
   Reject runs contaminated by another process or a one-rank collective stall.
   If an external sweep rotates work across GPUs, wait for its controller to
   exit instead of racing a momentarily idle sample.

## Analyze Traces

Start with the bundled dependency-free summarizer:

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/local-conventions.md}"
ANALYZER="$INFRA_SKILLS_HOME/skills/profile-serving-timeline/scripts/summarize_torch_trace.py"
RUN_DIR=/absolute/path/to/benchmark/YYYYMMDD_model_system_profile

python "$ANALYZER" \
  --step-regex 'forward_cudagraph' \
  "$RUN_DIR"/profiles/lmdeploy_rank*.json.gz

python "$ANALYZER" \
  --step-regex 'execute_context_.*generation' \
  "$RUN_DIR"/profiles/*.pt.trace.json.gz

python "$ANALYZER" \
  --step-regex 'step\[' \
  "$RUN_DIR"/profiles/<sglang-profile-dir>/*.trace.json.gz
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

- launch/workload commands and capture timing: phase, delay, duration,
  client-submit timing, active-request evidence, and trace count;
- median forward/cycle timing, cross-rank spread, strict kernel-family table,
  baseline/candidate deltas, and remaining bottlenecks;
- profiler perturbation, cross-system caveats, excluded/recaptured traces,
  cleanup status, and planned or completed profiler-free benchmark.

Retain commands, payloads, timestamps, metrics snapshots, traces, analyzer
output, and successful logs. Remove only disposable compile/autotune caches
after confirming they are not needed for another controlled launch.
