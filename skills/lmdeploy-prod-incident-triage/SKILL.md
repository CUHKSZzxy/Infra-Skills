---
name: lmdeploy-prod-incident-triage
description: Use when an LMDeploy production incident needs evidence preservation and replay.
---

# LMDeploy Production Triage

Preserve transient state before disruptive actions. Reuse existing bundles,
decisive logs, or a clean reproducer; evidence collection is not a ritual to
repeat after the likely owner is known.

## Evidence

When live state is needed, use the best-effort read-only collector:

```bash
python "$INFRA_SKILLS_HOME/skills/lmdeploy-prod-incident-triage/scripts/incident_artifact_tool.py" collect-bundle \
  --base-url http://127.0.0.1:23333 --outdir /tmp/lmdeploy_incident_bundle
python "$INFRA_SKILLS_HOME/skills/lmdeploy-prod-incident-triage/scripts/incident_artifact_tool.py" summarize-bundle \
  /tmp/lmdeploy_incident_bundle
```

Resolve `INFRA_SKILLS_HOME` from
[machine conventions](../../docs/conventions/machines.md); add
`--token "$LMDEPLOY_API_KEY"` when auth is enabled. The collector probes health,
models, metrics, sleeping state, DistServe engine info, and proxy node status.
Capture during traffic for load-dependent symptoms.

Preserve the exact request/workload, endpoint, model revision, template,
backend/topology, quant/KV settings, stream/output/concurrency policy, and logs
around the failure. For crashes or hangs, preserve per-rank stacks before
restarting when possible. Existing dumps/logs can substitute for an unreachable
server; keep credentials out of the artifacts.

## Interpretation And Replay

| Signal | Boundary to investigate |
| --- | --- |
| `/v1/models` fails | Reachability, auth, startup, route wiring |
| Models work, health fails | Backend health, sleep state, scheduler, child process |
| `lmdeploy:num_api_requests_waiting` grows | API-side admission/backpressure |
| `lmdeploy:num_requests_waiting` grows | Scheduler, KV capacity, batching |
| `lmdeploy:gpu_cache_usage_perc` near saturation | KV/token capacity |
| High TTFT, low queue time | Preprocessing, RPC, prefill |
| High TPOT/ITL | Decode, cache, generation workload |
| Abnormal DistServe engine info or proxy node status | Node health, routing, prefill/decode connections |
| Wrong output after deployment | Revision, template/preprocessing, generation config |

Replay request-dependent failures on a separate local/test target with the same
configuration; production restart is not part of preparing that target. Use a
single request for request-shaped failures or a fixed-load workload for capacity
and queue symptoms. Compare replay evidence with the original incident. If a
known-good/bad commit pair would narrow an unresolved regression, use a
deterministic good/bad harness with `git bisect run` in an isolated checkout.
Profile only when an execution question remains.

## Handoff Or Fix

Use `lmdeploy-runtime-debugging` for API/worker/RPC failures,
`benchmark-efficiency` for capacity/speed comparisons,
`lmdeploy-attention-dataflow` for KV/dispatch contracts, `optimize-kernel` for an
identified kernel, or `support-new-model` for architecture/preprocessing support.

A triage-only request ends with the evidence path, reproduction status, likely
owner and supporting signals, next action, and unresolved production risk. If a
fix is requested, continue through it and validate the original reproduction.
