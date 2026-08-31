# Deployment Context Convention

Use this with any benchmark run that reports accuracy, throughput, or latency.
The deployment context records the deployment space needed to reproduce and
interpret the result. Keep the common checklist here; benchmark skills should
link here and add only task-specific fields.

## Location

Create `$RUN_DIR/context/` during run setup. Use
`context/deployment_context.md` as the human-readable entry point and
`context/commands/` for exact server and client command lines.

For local runs, prefer the bundled helper:

```bash
bash "$SKILL_DIR/scripts/capture_context.sh" "$RUN_DIR" "$SOURCE_CHECKOUT" [config.sh]
```

The helper should write these files when the information is available:

- `deployment_context.md`: high-level deployment-space record.
- `commands/`: one `.cmd` file per exact command line.
- `config.sh.snapshot`: benchmark config at capture time, when provided.
- `git.txt`: source checkout branch, commit, remotes, and dirty status.
- `python.txt`: interpreter and relevant package versions.
- `gpu.txt`: accelerator inventory, topology, and utilization snapshot.
- `os.txt`: host OS and CPU snapshot.
- `env.filtered`: relevant non-secret environment variables.
- `model.txt`: model identifiers and local config hashes.

## Required Layers

Use automatic capture for stable machine/runtime facts. Manually fill only
fields that materially affect benchmark interpretation, such as model,
workload, topology, key commands, and acceptance/SLO thresholds. Record
inaccessible or remote-only fields as `unknown` or `null`; do not invent values.

- Model: local model path or API model id, served alias, tokenizer path when it
  differs, dtype or weight format, and local config hashes when available.
- Serving scenario: modality, dataset or synthetic workload, dataset
  source/path/split, sample count and start offset, input/output length policy,
  generation settings, request concurrency or rate policy, timeout, extra
  request body, and SLO or acceptance thresholds.
- Topology: endpoint path, backend, deployment architecture such as colocated,
  PD, or EPD, TP/PP/DP/EP, server replicas, proxy/router path, admission or
  queue limits, quantization, KV-cache settings, visible devices, and full
  server extra args.
- Versioned runtime profile: source checkout path, branch, commit, dirty
  status, package import path, Python/conda env, relevant client and runtime
  package versions, CUDA driver/runtime, collectives such as NCCL, and
  container image/digest when used.
- Accelerator platform: hostname or node, GPU model/count, visible GPU ids,
  interconnect/topology, memory, utilization, power, clocks, and any known
  MIG/container/resource limits.
