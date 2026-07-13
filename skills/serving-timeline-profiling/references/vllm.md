# vLLM PyTorch timeline

Use vLLM's worker profiler and HTTP capture controls. The canonical upstream
page is <https://docs.vllm.ai/en/stable/contributing/profiling/>.
`--profiler-config` requires vLLM 0.13 or later.

## Launch

Add a minimal profiler configuration to the otherwise real serve command:

```bash
vllm serve /path/to/model \
  --served-model-name model-alias \
  <real serving flags> \
  --profiler-config \
  '{"profiler":"torch","torch_profiler_dir":"/absolute/profile/path","torch_profiler_with_stack":false}'
```

For versions that expose them, `ignore_frontend=true` reduces unrelated
frontend events and `max_iterations=<small cap>` bounds accidental captures:

```text
{"profiler":"torch","torch_profiler_dir":"/profiles","torch_profiler_with_stack":false,"ignore_frontend":true,"max_iterations":96}
```

Confirm version-specific keys with `vllm serve --help`; fall back to the
documented minimal JSON if rejected. Gzip traces and the CUDA self-time table
are enabled by default in current vLLM.

For Docker, bind-mount the output directory at exactly
`torch_profiler_dir`. Mount the whole Hugging Face model cache/root rather than
only a snapshot if snapshot files contain relative symlinks.

## Capture

For steady decode:

1. Start a few long concurrent requests.
2. Poll `/metrics` until all requests are running and generated tokens advance.
3. Start profiling:

   ```bash
   curl --noproxy '*' --fail-with-body --silent --show-error \
     -X POST http://127.0.0.1:8000/start_profile
   ```

4. Wait 0.5-2 seconds.
5. Stop and flush:

   ```bash
   curl --noproxy '*' --fail-with-body --silent --show-error \
     --max-time 600 \
     -X POST http://127.0.0.1:8000/stop_profile
   ```

For prefill, call `/start_profile` before submitting the requests. The stop
call waits for trace flushing and can take minutes; do not kill it merely
because the requested capture was short.

## Guardrails

- Do not use `--enforce-eager` only for profiling. Preserve the graph mode used
  for real performance unless eager-versus-graph behavior is the hypothesis.
- Finish JIT, autotuning, CUDA-graph capture, and DeepGEMM/library warmup before
  `/start_profile`. Do not skip warmup except in an explicit startup study.
- Avoid custom profiling-scope environment variables in the first comparable
  run. They can alter Dynamo graphs and compile-cache keys; add them only as a
  separate diagnostic variant.
- Keep requests few and the window short. Trace flush cost grows rapidly.
- Expect one `.pt.trace.json.gz` and one profiler table per worker/rank. Verify
  rank/world/device metadata rather than trusting filenames alone.
- Do not use server throughput buckets overlapping profiler start/stop or
  flushing as benchmark results.
