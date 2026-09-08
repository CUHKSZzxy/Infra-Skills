---
name: profile-serving-timeline
description: Use when capturing or analyzing LMDeploy, vLLM, or SGLang serving traces.
---

# Serving Timeline Analysis

For supplied traces, analyze the available evidence first. Capture new traces
only when requested or when a missing phase/rank prevents the requested
conclusion. Use `benchmark-efficiency` for serving throughput/latency claims.

## Capture Contract

- Define the phase (startup, prefill, steady decode, or mixed traffic) and
  workload. For comparisons, preserve checkpoint, source/import path, topology,
  graph mode, quantization, backend, and all flags except the intended variable.
- For a new capture, read the serving-system reference:
  [LMDeploy](references/lmdeploy.md), [vLLM](references/vllm.md), or
  [SGLang](references/sglang.md). Each has different start/stop and flush behavior.
- For steady-state measurements, warm the exact measured batch/graph key and
  runtime branch. Do not disable graph mode or library warmup to simplify a
  trace. Startup or warmup studies should capture those phases explicitly.
- Submit prepared requests and arm/stop profiling from a script so agent delay
  does not enter the window. For steady decode, confirm requests are running
  and tokens advance. Use the system's short capture window; widen or realign
  it when timestamps show that client setup/retries missed the target phase.
- Flush profiling before cancelling workload processes. Check expected rank
  files parse and contain the intended phase, annotations, and kernel branch.
  Empty/idle-only captures cannot answer a steady-execution question. Preserve
  evidence of crashes or stalls; do not discard it as a bad capture merely
  because execution did not complete.
- For timing comparisons, record GPU memory, utilization, power, and clocks.
  Recapture confirmed interference or mismatched windows. A repeatable rank
  stall may be the finding; investigate it rather than averaging it away.

Use [artifact conventions](../../docs/conventions/benchmark-artifacts.md) for
capture files, payloads, logs, and summaries. Clean up processes started for the
capture after their dumps finish; leave pre-existing services running.

## Analysis

The dependency-free `scripts/summarize_torch_trace.py` accepts trace paths,
`--step-regex`, and repeated `--group NAME=REGEX`. Resolve the script from
`INFRA_SKILLS_HOME` in [machine conventions](../../docs/conventions/machines.md).
Typical step patterns are `forward_cudagraph` for LMDeploy,
`execute_context_.*generation` for vLLM, and `step\[` for SGLang; use annotations
actually present in the target traces.

Compare forward duration and start-to-start interval, cross-rank spread,
kernel-family duration/counts, and graph-child versus outside-graph launches.
Inspect host submission when it could explain GPU gaps; apparent synchronization
may belong to a background wait thread. Exact kernel groups and broad semantic
groups answer different questions; the first matching group owns each kernel.

Summed durations can exceed wall time across streams, and one CUDA-graph launch
can contain thousands of child kernels. Reciprocal cycle rate is trace-implied
cadence, not benchmark throughput. Exclude truncated boundary events from steady
statistics, retain genuine outliers, and report profiler perturbation.

## Completion

A diagnosis is complete when the requested boundary is explained with trace
evidence and remaining uncertainty is stated. Use targeted NCU evidence only
when an identified kernel's limiting resource remains unclear. Run a separate
profiler-free benchmark when the task includes a serving-performance claim.

Summarize the relevant timing/rank/kernel comparisons with trace paths,
phase/window and exclusions, launch/workload provenance when available, and
remaining bottlenecks. For new captures, write `summary.md` and include cleanup
status. Do not invent missing provenance for supplied traces.
