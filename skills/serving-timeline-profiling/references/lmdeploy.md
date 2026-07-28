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
export LMDEPLOY_PROFILE_USE_GZIP=1

export PYTHONPATH=/path/to/lmdeploy/source
GPU_IDS=0
TP=1
export CUDA_VISIBLE_DEVICES="$GPU_IDS"

/path/to/python -m lmdeploy serve api_server /path/to/model \
  --backend pytorch \
  --tp "$TP" \
  --server-name 127.0.0.1 \
  --server-port 28888
```

Set `GPU_IDS` and `TP` to the minimum required by the model or comparison. Do
not allocate every available GPU unless the user explicitly requests an
all-GPU run.

Append the real serving flags under test. Do not add profiling-only model,
cache, graph, or eager overrides.

## Timer semantics

- `LMDEPLOY_PROFILE_DELAY` is counted by each model-agent profiler task after
  that agent loop starts. It is not tied to request readiness.
- The `Profiler start on rank[...]` warning is emitted while constructing the
  profiler, before the delay. It confirms profiler enablement, not the actual
  capture timestamp. Current code emits no separate delayed-start log.
- A positive `LMDEPLOY_PROFILE_DURATION` automatically stops and exports
  `<prefix><rank>.json.gz` by default. Set `LMDEPLOY_PROFILE_USE_GZIP=0` only
  when an uncompressed `.json` trace is required. Graceful shutdown also dumps
  an active profiler.
- Use a positive finite duration; duration `<=0` is unsupported for DP greater
  than one and makes accidental giant traces easier.
- Create the output directory first and use a fresh, absolute prefix. TP `N`
  should produce rank 0 through rank `N-1`.

Launch long concurrent requests as soon as the API is ready and ensure the
configured delay leaves time to reach the desired phase. A retrying client may
start before readiness. Client-side tokenizer or dataset initialization can
consume several seconds after the health check succeeds, so compare server,
client, and dump timestamps when choosing the delay. Because there is no HTTP
start/stop control, verify the trace annotations afterward instead of assuming
the timer caught steady decode.

## Validation and pitfalls

- Use `Profiler start on rank[...]` only as enablement evidence; require
  `dump to ...rankN.json.gz` for every expected rank with the default settings.
- Check every expected rank parses and contains the intended annotation, such
  as multiple complete `forward_cudagraph` cycles. Validate the phase and
  expected feature kernel from trace contents rather than inferring them from
  the enablement warning.
- Use a fresh output prefix for every retry. A previous nonempty rank file can
  otherwise make a failed recapture look successful.
- Exclude the first captured iteration and any collective crossing the trace
  boundary before computing steady medians.
- Inspect all expected ranks for mismatched windows and isolated NCCL stalls.
  Recapture a contaminated rank set instead of averaging the outlier away.
- Multi-rank traces can still be large even when compressed; check free disk
  first, especially before disabling gzip.
- Stop the server only after all rank dumps finish.

Use `LMDEPLOY_RAY_NSYS_ENABLE`, `LMDEPLOY_RAY_NSYS_OUT_PREFIX`, or the Ray
timeline variables only when PyTorch traces cannot answer the question; they
are a separate capture workflow.
