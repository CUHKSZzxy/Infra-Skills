---
name: lmdeploy-runtime-debugging
description: Use when LMDeploy serve or generation has runtime symptoms such as hanging curl, slow endpoints, streaming stalls, timeouts, stuck requests, concurrency-only latency, first-token delay, or confusing serve logs.
---

# LMDeploy Runtime Debugging

Use this for runtime behavior that is not clearly an environment, model-support,
attention-dataflow, or kernel-tuning problem.

Prefer the adjacent skills when the symptom is already classified:

- Env/Python/CUDA mismatch: `check-env`
- Attention, KV cache, quant policy, backend dispatch: `lmdeploy-attention-dataflow`
- CUDA/Triton correctness or speed: `triton-kernel-performance`
- New architecture or VLM implementation work: `support-new-model`

## Output Contract

When reporting progress or a final diagnosis, return:

- problem class,
- what was checked,
- strongest signal so far,
- current best guess,
- what was ruled out,
- next step,
- production or validation risk.

This keeps runtime debugging from becoming a loose log summary.

## 1. Build A Timeline First

Collect timestamps before changing code.

```bash
date
curl -w '\ntime_total=%{time_total}\n' -i http://127.0.0.1:<port>/<endpoint>
tail -n 200 <serve.log>
```

Record:

- server start time and "application startup complete"
- request launch time, concurrency, stream mode, model path, endpoint
- first log line per request/session
- first token or final response time
- endpoint probe time, such as health, metrics, or a small completion request

If the endpoint is slow only during a concurrent burst and fast afterward,
suspect server-loop or request-preparation contention before blaming the route
itself.

## 2. Classify The Stall Boundary

Map the delay to one boundary:

- startup/model load: before uvicorn reports startup complete
- HTTP accept/routing: no handler log appears
- request parse/validation: body received but no engine/session log
- prompt/template/tokenizer prep: chat template, tokenization, `get_input_prompt`
- VLM prep: image/video decode, preprocess, wrap, vision forward
- engine queue: request enters engine but waits behind active work
- GPU decode/prefill: kernels run, token throughput changes
- streaming/client: server emits chunks but client waits
- network/proxy: local `127.0.0.1` differs from remote or `0.0.0.0`

Do not fix the symptom endpoint until the boundary is known.

If a crash dump, request dump, or exact failing payload already exists, preserve
it and replay it before starting profiler work. Use profiling after the problem
is reproducible and queueing, routing, or request-preparation explanations are
mostly ruled out.

Load `references/api-server-mp-engine-zmq.md` when the boundary crosses
FastAPI, `AsyncEngine`, PyTorch MP engine, or ZMQ RPC.

## 3. Separate Sandbox And Server Reachability

When testing LMDeploy through a local agent client such as Codex, first prove
whether the client sandbox can reach the server. A sandbox with network disabled
can make `curl http://0.0.0.0:<port>/...` fail even when Uvicorn is healthy.

Use a cheap endpoint before debugging generation:

```bash
curl -fsS http://0.0.0.0:<port>/v1/models -H 'Authorization: Bearer <key>'
```

If the probe fails inside the agent sandbox, retry the same probe through the
approved network-capable path. Only inspect LMDeploy code after an outside-
sandbox probe also fails or server logs show request handling errors. For local
Codex smoke tests, unset proxy variables in the script and keep runtime writes
under a guarded scratch directory.

For OpenAI-compatible agent endpoints, grow validation in layers: raw text curl,
streaming/tool curl, agent no-tool smoke, agent read-tool smoke, agent write-tool
smoke, then a multi-step tool-output-continuation smoke with exact file checks.
This separates protocol bugs from model prompt variance and local sandbox
issues.

## 4. Probe At Boundaries

Add temporary logs only around component boundaries, then remove them before the
final patch.

Useful probe fields:

- monotonic elapsed time, session/request id, stage name
- input token count, max new tokens, stream mode
- whether work is synchronous, `await`ed, or submitted to an executor
- executor queue behavior when concurrency is high

When a large request appears stuck after preprocessing, use process and stack
probes before assuming GPU prefill is slow. Compare `top`/`nvidia-smi` memory
with Python stacks from `py-spy`, `pd`, or an equivalent sampler for the API
process and engine worker. If the API process is busy serializing or sending a
large payload while the worker waits to receive it, inspect the handoff payload
for tensor views, duplicated buffers, or other objects whose backing storage is
much larger than their logical request slice.

For event-loop responsiveness, compare a tiny endpoint probe while the workload
is active:

```bash
while true; do
  date '+%H:%M:%S'
  curl -s -o /dev/null -w 'time_total=%{time_total}\n' http://127.0.0.1:<port>/<endpoint>
  sleep 1
done
```

## 5. Compare Low And Concurrent Load

Run the same request shape at low and high concurrency.

- low load slow: inspect the single-request stage timeline
- high load slow only: inspect shared CPU work, locks, executor queues, and GIL-heavy preprocessing
- endpoint probe slow but generation throughput normal: suspect server event-loop starvation
- generation throughput drops: inspect engine scheduling, GPU kernels, or model workload

Keep the workload fixed: model, prompt/media, max tokens, stream flag, backend,
GPU, and checkout.

Quick direction hints:

- startup or health failure: inspect startup logs, model load, CUDA OOM, and
  route/auth mismatch before request-level profiling
- TTFT spike: check queue depth, first handler timestamp, prompt/VLM prep time,
  and prefill start before decode kernels
- throughput collapse: compare request queueing, cache hit behavior, scheduler
  pressure, and decode throughput
- wrong output: preserve the exact request, model revision, chat template, and
  preprocessing path before changing generation code
- timeout or hang: collect per-rank logs and process stacks before assuming a
  single endpoint is at fault

## 6. Patch The Blocking Boundary

Pick the smallest fix that addresses the classified boundary.

Common LMDeploy runtime fixes:

- move CPU-heavy synchronous prep off the FastAPI event loop
- avoid submitting a large burst of GIL-heavy work into a single-worker executor
- gate executor submissions with an async lock so waiters yield to the loop
- keep health/metrics on the normal server port unless a separate port is proven necessary
- preserve engine and GPU decode behavior when the bottleneck is request prep

Before finishing:

- remove temporary debug logs and local benchmark files
- stage only intended files
- validate with a narrow compile/test plus the original reproduction
- state what was and was not measured
