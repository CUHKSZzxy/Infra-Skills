# E2E Efficiency Result Schema

Use this reference only when a local LMDeploy benchmark run has more than a
simple baseline/candidate pair, such as a feature matrix, KV-cache variant
matrix, backend variant, or several failed attempts that should remain
auditable.

## JSONL Row

Write one JSON object per candidate. Keep failed, skipped, timeout, and OOM
rows in the same file as successful rows.

Required shape:

```json
{
  "engine": "pytorch",
  "api_backend": "lmdeploy-chat",
  "candidate_id": "tp2_kvfp8",
  "model": "qwen35_35b_a3b",
  "status": "ok",
  "failure_reason": "",
  "hardware": {
    "gpu_model": "NVIDIA H100",
    "gpu_count": 2,
    "visible_devices": "0,1"
  },
  "workload": {
    "dataset": "sharegpt",
    "input_len": null,
    "output_len": 2048,
    "num_prompts": 1000,
    "endpoint": "/v1/chat/completions"
  },
  "metrics": {
    "request_throughput": 12.34,
    "output_token_throughput": 5678.9,
    "total_token_throughput": 6789.0,
    "mean_ttft_ms": 321.0,
    "mean_tpot_ms": 12.3,
    "mean_itl_ms": 12.1,
    "success_rate": 1.0
  },
  "sla": {
    "max_mean_ttft_ms": 2000,
    "max_mean_tpot_ms": 80,
    "min_success_rate": 0.99,
    "passed": true
  },
  "server_command": "lmdeploy serve api_server ...",
  "benchmark_command": "python profile_restful_api.py ...",
  "artifacts": {
    "server_log": "0_serve_logs/tp2_kvfp8.log",
    "benchmark_log": "0_bench_logs/tp2_kvfp8_sharegpt_out_2048_prompts_1000.log",
    "raw_result": "0_analysis/results.jsonl"
  }
}
```

## Status Values

- `ok`: benchmark finished and metrics are trustworthy.
- `failed`: command failed for a known non-OOM reason.
- `oom`: model or candidate exhausted GPU or host memory.
- `timeout`: server or benchmark timed out.
- `skipped`: intentionally not run, with a reason in `failure_reason`.

Do not write `0` as a placeholder for missing latency or throughput metrics.
Leave the field out or set it to `null` so ranking does not treat an unknown
measurement as a real zero.

## Ranking Rule

Default ranking:

1. `status == "ok"`
2. `sla.passed == true`
3. higher `metrics.request_throughput`
4. higher `metrics.output_token_throughput`
5. lower `metrics.mean_ttft_ms`
6. lower `metrics.mean_tpot_ms`
7. lower `hardware.gpu_count`

If the user cares more about token throughput than request throughput, swap
steps 3 and 4 and state that in `summary.md`.

## Summary Tables

For a matrix run, put these tables near the top of `summary.md`:

- `Selected Results`: selected LMDeploy baseline/candidate or best row per
  workload.
- `Comparison`: per-workload deltas for request throughput, output token
  throughput, TTFT, and TPOT/ITL.
- `Failed Or Skipped Candidates`: every non-selected candidate with status,
  failure reason, command, and artifact path.

Keep config blocks and exact commands below the tables unless the command itself
is the main result.
