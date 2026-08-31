# Benchmark Artifact Conventions

Use [machines.md](machines.md) to identify the measured checkout, such as
`LMDEPLOY_DEV_SOURCE`, `VLLM_DEV_SOURCE`, or `SGLANG_DEV_SOURCE`.

Keep local end-to-end accuracy and speed outputs inside the measured checkout:

```text
<source-checkout>/benchmark/<YYYYMMDD>_<model>_<dataset-or-workload>[_<feature>]/
```

Honor a user-provided destination. Otherwise use lowercase, shell-friendly
labels under `benchmark/`, not ad hoc top-level `bench_*` folders. Prefix the
folder with the local run-start date as `YYYYMMDD_`; never append the date as a
suffix, and do not add an `e2e_` marker. Keep that prefix when a run is resumed
or crosses midnight. State the assumed checkout before a long run when the
destination is ambiguous.

Put `summary.md` at the run root. Keep deployment context in a separate
`context/` folder following [deployment-context.md](deployment-context.md).
Create other artifact folders only when they will receive files:

- `serve_logs/`: server, proxy, controller, and worker stdout/stderr.
- `bench_logs/`: performance benchmark client stdout/stderr.
- `accuracy/`: accuracy client stdout, JSON/JSONL/TSV results, endpoint
  probes, response samples, and parser outputs.
- `profiles/`: profiler trace outputs such as `.json`, `.db`, `.ncu-rep`, or
  compressed trace archives.
- `profile_workload/`: request payloads, launch commands, and client logs used
  only to drive a profiler capture.
- `workload/`: generated or adapted benchmark input/request files.
- `analysis/`: derived summaries, comparison CSVs/plots, post-hoc scripts, and
  investigation notes.

Do not precreate `analysis/` or other placeholder folders just because a
template names them. Do not add numeric prefixes. Store server and client logs
with the run so comparisons remain auditable. Final reports must include the
run folder, exact `summary.md` path, and exact `context/deployment_context.md`
path.

Do not assume datasets exist on a fresh machine. Pass paths explicitly with
`DATASET_PATH` or the script-specific `--data-path`.
