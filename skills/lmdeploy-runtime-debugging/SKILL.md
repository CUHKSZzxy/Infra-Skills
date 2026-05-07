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

## 3. Probe At Boundaries

Add temporary logs only around component boundaries, then remove them before the
final patch.

Useful probe fields:

- monotonic elapsed time, session/request id, stage name
- input token count, max new tokens, stream mode
- whether work is synchronous, `await`ed, or submitted to an executor
- executor queue behavior when concurrency is high

For event-loop responsiveness, compare a tiny endpoint probe while the workload
is active:

```bash
while true; do
  date '+%H:%M:%S'
  curl -s -o /dev/null -w 'time_total=%{time_total}\n' http://127.0.0.1:<port>/<endpoint>
  sleep 1
done
```

## 4. Compare Low And Concurrent Load

Run the same request shape at low and high concurrency.

- low load slow: inspect the single-request stage timeline
- high load slow only: inspect shared CPU work, locks, executor queues, and GIL-heavy preprocessing
- endpoint probe slow but generation throughput normal: suspect server event-loop starvation
- generation throughput drops: inspect engine scheduling, GPU kernels, or model workload

Keep the workload fixed: model, prompt/media, max tokens, stream flag, backend,
GPU, and checkout.

## 5. Patch The Blocking Boundary

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
