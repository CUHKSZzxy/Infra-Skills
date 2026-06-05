---
name: lmdeploy-prod-incident-triage
description: Use when a live or recent LMDeploy server has production serving symptoms such as unhealthy health checks, queue growth, latency or throughput regressions, timeouts, crashes, wrong outputs after deploys, or DistServe/proxy issues.
---

# LMDeploy Production Incident Triage

Use this to turn a live or recent LMDeploy serving problem into a reproducible
debug path. Start with read-only evidence, preserve the triggering request or
workload, replay on a clean target, then switch to the focused skill that owns
the narrowed boundary.

Do not start with profiling or code changes. Production triage is first about
capturing enough evidence that the problem can be replayed and compared.

Pair with:

- `lmdeploy-runtime-debugging` after the issue is narrowed to API server,
  request preparation, AsyncEngine, MP engine, ZMQ, streaming, or sandbox
  reachability.
- `e2e-efficiency-benchmark` when the reproducer is a serving speed or capacity
  comparison.
- `lmdeploy-attention-dataflow` or `triton-kernel-performance` when replay
  points to attention, KV cache, kernels, or backend dispatch.
- `support-new-model` when wrong output or crashes are tied to model/VLM
  architecture support.

## Output Contract

Return:

- problem class
- incident bundle path, if collected
- exact reproducer or why one is not available yet
- what was checked
- strongest signal so far
- current best guess
- what was ruled out
- next tool or next step
- production risk

## 1. Collect A Read-Only Bundle

If a server is reachable, collect a bundle before changing flags, restarting,
profiling, or patching code:

```bash
python skills/lmdeploy-prod-incident-triage/scripts/incident_artifact_tool.py collect-bundle \
  --base-url http://127.0.0.1:23333 \
  --outdir /tmp/lmdeploy_incident_bundle

python skills/lmdeploy-prod-incident-triage/scripts/incident_artifact_tool.py summarize-bundle \
  /tmp/lmdeploy_incident_bundle
```

If auth is enabled:

```bash
python skills/lmdeploy-prod-incident-triage/scripts/incident_artifact_tool.py collect-bundle \
  --base-url http://127.0.0.1:23333 \
  --token "$LMDEPLOY_API_KEY" \
  --outdir /tmp/lmdeploy_incident_bundle
```

The bundle collects best-effort responses for:

- `/health`
- `/v1/models`
- `/metrics`
- `/is_sleeping`
- `/distserve/engine_info`
- `/nodes/status` for proxy-style deployments

If the bundle was captured while the server was idle, recollect during traffic
or move quickly to a request/workload replay.

If no live server is reachable, start from the best artifact already available:
serve logs, crash logs, exact request body, benchmark command, process stacks,
GPU state, OTel/trace data, or a known good/bad commit pair.

## 2. Preserve The Trigger

Save the smallest trigger that reproduces the incident:

- exact JSON request body and endpoint
- auth shape without secrets
- model alias, backend, TP/DP, quant/KV-cache settings, DistServe/proxy flags
- stream mode, max tokens, prompt/media shape, concurrency, and client timeout
- server logs around the request window

For request-level issues, write a `repro_request.json` plus a `replay.sh` curl
or benchmark command. For crashes and hangs, preserve per-rank logs and process
stacks before restarting if possible.

Do not jump from a live symptom straight to low-level debugging without saving
something that can be rerun.

## 3. Replay On A Clean Target

Replay before profiling:

1. restart a clean target with the same checkout, env, model, backend, and flags
2. run the preserved request or benchmark workload
3. collect replay-time logs, `/health`, `/metrics`, and process/GPU state
4. compare with the production bundle

Use a single request first for wrong output, crash, or request-shaped timeout.
Use a fixed-concurrency benchmark for queue growth, latency, throughput, or
capacity regressions.

If one commit is known-good and another is known-bad, build a deterministic
harness before manual deep debugging:

1. choose request replay, benchmark command, or correctness check
2. make it exit `0` on good behavior and non-zero on bad behavior
3. run `git bisect start <bad> <good>`
4. run `git bisect run <harness>`

## 4. Read The Main Signals

Use the bundle summary plus logs to classify the incident:

- `/v1/models` fails: HTTP reachability, auth, server startup, or route wiring.
- `/v1/models` works but `/health` is unhealthy: backend health probe,
  sleeping state, scheduler progress, or engine child process.
- `lmdeploy:num_api_requests_waiting` grows: request handles or API-side
  backpressure before engine execution.
- `lmdeploy:num_requests_waiting` grows: scheduler, KV capacity, or engine-side
  batching pressure.
- `lmdeploy:gpu_cache_usage_perc` near saturation: KV-cache/token capacity
  pressure.
- TTFT high with queue time low: prefill, prompt/VLM preprocessing, RPC handoff,
  or first-token engine path.
- TPOT/ITL/decode time high: decode kernels, KV cache, attention backend, or
  generation workload.
- `/distserve/engine_info` or proxy `/nodes/status` abnormal: DistServe/proxy
  routing, node health, or prefill/decode connection state.
- wrong output after deploy: preserve request, model revision, tokenizer/chat
  template, preprocessing path, and generation config before changing code.

## 5. Switch Tools After The Boundary Is Clear

Switch only after bundle plus replay classify the likely owner:

- API/routing/preprocessing/AsyncEngine/MP/ZMQ/streaming:
  `lmdeploy-runtime-debugging`
- speed/capacity comparison:
  `e2e-efficiency-benchmark`
- attention, KV cache, quant policy, FA3, FlashMLA, backend dispatch:
  `lmdeploy-attention-dataflow`
- CUDA/Triton kernel correctness or performance:
  `triton-kernel-performance`
- model/VLM architecture, preprocessing, or weight-loading support:
  `support-new-model`

Do not switch tools before collecting the first bundle unless the user already
has decisive logs, dumps, or a clean reproducer.
