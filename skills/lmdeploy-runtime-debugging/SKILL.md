---
name: lmdeploy-runtime-debugging
description: Use when diagnosing local or reproduced LMDeploy serving hangs, latency, streaming, or worker failures.
---

# LMDeploy Runtime Debugging

Locate the delayed or failing boundary, fix its cause when requested, and
validate against the original reproduction. For a live production incident
that still needs evidence preservation, use `lmdeploy-prod-incident-triage`.
Use `check-env` when Python, CUDA, or import wiring is the likely cause.

## Establish The Boundary

Start from available logs, timestamps, request dumps, and process state. Replay
an existing failing payload before creating a new workload. Preserve exact
model/config, prompt or media, concurrency, output length, and stream mode.

For reachability failures, probe `/v1/models` on `127.0.0.1` with a bounded
client timeout and appropriate auth. If the agent sandbox blocks the probe,
retry through an available approved network path. Compare direct and proxied
access before treating a client connectivity failure as an LMDeploy bug.

| Signal | Likely boundary to inspect |
| --- | --- |
| No startup-complete message | Model load, CUDA OOM, worker readiness |
| No handler log | HTTP routing, auth, network/proxy |
| Handler active, no engine/session log | Validation, template/tokenizer or VLM preparation |
| Request queued before GPU work | Engine scheduling, KV capacity, admission limits |
| High TTFT with little queue time | Preprocessing, RPC handoff, prefill |
| Slow TPOT/ITL | Decode kernels, cache path, generation workload |
| Server emits chunks but client waits | Streaming/client buffering or proxy |
| Tiny endpoint slows only during a burst | Event-loop starvation, shared CPU work, executor queues |

These are hypotheses; use timestamps or stacks to distinguish them. Compare
low and concurrent load with the same request shape when contention is in
question. Collect per-rank logs and process stacks for hangs before assuming
GPU execution is responsible.

## Focused Investigation

Read only relevant sections of
[API server, MP engine, and ZMQ dataflow](references/api-server-mp-engine-zmq.md)
when the boundary crosses FastAPI, `AsyncEngine`, engine workers, or RPC:

- request replay checks for protocol errors or multimodal templates;
- large payload handoffs when serialization/storage size may explain a stall;
- DP/proxy startup hangs when children never reach readiness or registration.

Add temporary probes at component boundaries when existing evidence is
insufficient: monotonic elapsed time, request ID, input/output token counts,
stream mode, and synchronous versus awaited/executor work. Profile when the
remaining question is GPU execution; do not require a trace to diagnose an
already-localized routing or preparation failure.

Typical fixes depend on the evidence: move synchronous preparation off the
FastAPI event loop, bound GIL-heavy executor submissions, or let waiters yield
through an async lock. Preserve normal health/metrics routing and engine
behavior unless they own the failure.

## Completion

For a fix, remove temporary probes and validate with the original reproduction
plus checks for affected behavior. For diagnosis only, report the evidence-backed
boundary, validation gaps, and next useful step.
