# LMDeploy PyTorch timeline

Use the integrated PyTorch profiler for short CPU/CUDA Chrome traces. The
canonical upstream page is
<https://lmdeploy.readthedocs.io/en/latest/advance/pytorch_profiling.html>.

## Launch

Set the profiler variables before starting the PyTorch API server:

```bash
RUN_DIR=/absolute/path/to/benchmark/e2e_<run>
mkdir -p "$RUN_DIR/0_profiles" "$RUN_DIR/0_serve_logs"

export LMDEPLOY_PROFILE_CPU=1
export LMDEPLOY_PROFILE_CUDA=1
export LMDEPLOY_PROFILE_DELAY=30
export LMDEPLOY_PROFILE_DURATION=1
export LMDEPLOY_PROFILE_OUT_PREFIX="$RUN_DIR/0_profiles/lmdeploy_rank"

export PYTHONPATH=/path/to/lmdeploy/source
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

/path/to/python -m lmdeploy serve api_server /path/to/model \
  --backend pytorch \
  --tp 8 \
  --server-name 127.0.0.1 \
  --server-port 28888
```

Append the real serving flags under test. Do not add profiling-only model,
cache, graph, or eager overrides.

## Timer semantics

- `LMDEPLOY_PROFILE_DELAY` is counted by each model-agent profiler task after
  that agent loop starts. It is not tied to request readiness.
- The `Profiler start on rank[...]` warning is emitted while constructing the
  profiler, before the delay. It confirms profiler enablement, not the actual
  capture timestamp. Current code emits no separate delayed-start log.
- A positive `LMDEPLOY_PROFILE_DURATION` automatically stops and exports
  `<prefix><rank>.json`. Graceful shutdown also dumps an active profiler.
- Use a positive finite duration; duration `<=0` is unsupported for DP greater
  than one and makes accidental giant traces easier.
- Create the output directory first and use a fresh, absolute prefix. TP8
  should produce rank 0 through rank 7.

Launch long concurrent requests as soon as the API is ready and ensure the
configured delay leaves time to reach the desired phase. A retrying client may
start before readiness. Because there is no HTTP start/stop control, verify the
trace annotations afterward instead of assuming the timer caught steady
decode.

## Validation and pitfalls

- Use `Profiler start on rank[...]` only as enablement evidence; require
  `dump to ...rankN.json` for every expected rank.
- Check every expected rank parses and contains the intended annotation, such
  as `forward_cudagraph`. Validate the phase from trace contents rather than
  inferring it from the enablement warning.
- Exclude the first captured iteration and any collective crossing the trace
  boundary before computing steady medians.
- Raw multi-rank JSON can exceed a gigabyte even for a one-second full-model
  capture; check free disk first.
- Stop the server only after all rank dumps finish.

Use `LMDEPLOY_RAY_NSYS_ENABLE`, `LMDEPLOY_RAY_NSYS_OUT_PREFIX`, or the Ray
timeline variables only when PyTorch traces cannot answer the question; they
are a separate capture workflow.
