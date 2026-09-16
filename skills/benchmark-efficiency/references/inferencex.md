# InferenceX AgentX Serving Benchmarks

## Client and deployment

The inspected workflow uses the **SemiAnalysisAI AgentX Harness fork of
AIPerf**, not a generic `aiperf` installation. Its recorded source revision is
`56a0cf70f4c0359454ee4bd15a17770b541a3e3e`, reporting AIPerf 0.12.0 with
Python 3.12. Treat this as a reproduction pin, not a claim about the latest
release. Use a separate client environment, record its source revision, and
confirm `aiperf profile --help` includes `--scenario inferencex-agentx-mvp`.
A version string alone does not identify the fork.

To reproduce that client in a prepared environment, install the pinned public
source using that environment's interpreter:

```bash
: "${CLIENT_PYTHON:?}"
"$CLIENT_PYTHON" -m pip install \
  'aiperf @ https://github.com/SemiAnalysisAI/agentx-harness/archive/56a0cf70f4c0359454ee4bd15a17770b541a3e3e.tar.gz'
```

Record the LMDeploy checkout/version separately. Set `AIPERF_BIN` to the client
executable, `TOKENIZER_PATH` to the matching tokenizer directory, `MODEL_NAME`
to the served API name, `BENCH_BASE_URL` to the base URL ending in `/v1`, and
`RUN_DIR` / `TRIAL_LABEL` to the artifact root and unique variant/trial label.
Keep server-only `PYTHONPATH` changes out of the client environment. Configure
`NO_PROXY` and `no_proxy` for the selected endpoint host.

For a direct server, wait for readiness and verify `/v1/models`. For routed DP,
start the router and optional KV-store service, then workers; verify every
expected worker is registered (for the inspected router, `/nodes/status`) and
probe the router's OpenAI endpoint. Record routing policy and topology.
Mooncake is an optional deployment component, not an InferenceX requirement;
keep its memory allocation, transport, and cache state explicit if enabled.
Model-specific tool/reasoning parsers belong to the server configuration.

## Agentic replay example

This is a 30-minute workload with concurrency 40, not a recommended capacity
for every model. Confirm the chosen deployment can support the workload before
measurement; record changes to concurrency as a different configuration.

```bash
set -euo pipefail
: "${AIPERF_BIN:?}" "${BENCH_BASE_URL:?}" "${MODEL_NAME:?}"
: "${TOKENIZER_PATH:?}" "${RUN_DIR:?}" "${TRIAL_LABEL:?}"
mkdir -p "$RUN_DIR/context/commands" "$RUN_DIR/bench_logs/$TRIAL_LABEL"
export AIPERF_DATASET_CONFIGURATION_TIMEOUT=1800
export AIPERF_SERVICE_PROFILE_CONFIGURE_TIMEOUT=1800
export AIPERF_HTTP_KEEPALIVE_TIMEOUT=4
cmd=("$AIPERF_BIN" profile --scenario inferencex-agentx-mvp
  --url "$BENCH_BASE_URL" --model "$MODEL_NAME"
  --tokenizer "$TOKENIZER_PATH" --endpoint-type chat
  --public-dataset semianalysis_cc_traces_weka_062126_256k
  --max-context-length 256000
  --concurrency 40 --benchmark-duration 1800 --streaming
  --goodput 'time_to_first_token:3000 output_token_throughput_per_user:40'
  --use-server-token-count --extra-inputs ignore_eos:true
  --cache-bust first_turn_prefix --system-idle-gap-cap-seconds 10
  --trajectory-start-min-ratio 0.0 --trajectory-start-max-ratio 1.0
  --random-seed 1024 --ui simple
  --artifact-dir "$RUN_DIR/bench_logs/$TRIAL_LABEL/artifacts")
printf '%q ' "${cmd[@]}" > "$RUN_DIR/context/commands/${TRIAL_LABEL}_client.cmd"
printf '\n' >> "$RUN_DIR/context/commands/${TRIAL_LABEL}_client.cmd"
"${cmd[@]}" 2>&1 | tee "$RUN_DIR/bench_logs/$TRIAL_LABEL/aiperf.log"
```

The pinned scenario enforces streaming, ignore-EOS, first-turn prefix cache
busting, agentic timing, and a minimum 900-second benchmark duration (default
1,800). It forbids input truncation and ignoring trace delays. Do not silently
shorten it into a smoke test or replace it with a simple request loop. Validate
basic API connectivity separately, and keep any harness smoke result distinct
from a full scenario result. Preserve the scenario's warmup behavior and record
its effective configuration; total wall time includes setup, warmup, and drain.

Concurrency describes the agentic workload, not the server's maximum batch
size. Keep the dataset ID, context filter, seed, trajectory-start range,
trace-delay policy, and cache-busting mode fixed across comparisons. The client
context filter does not set LMDeploy's server session length. Check actual
server-reported input lengths rather than inferring them from the dataset name.
Verify streaming usage is present when using server token counts.

## Metrics and completion checks

Read `profile_export_aiperf.json`, per-request JSONL, effective configuration,
and client/server logs together. Preserve units and sample counts; keep warmup
records separate from profiling records. In the inspected export:

| Quantity | Field / interpretation |
| --- | --- |
| TTFT | `time_to_first_token`, milliseconds |
| TPOT-style decode latency | `inter_token_latency`, milliseconds; verify the pinned definition |
| Per-user output rate | `output_token_throughput_per_user`, tokens/sec/user |
| Actual input length | `input_sequence_length`, tokens |
| Aggregate serving rates | `request_throughput`, `output_token_throughput` |
| SLO-qualified rate | `goodput`, requests/sec |

The example goodput constraints require TTFT at most 3,000 ms and output rate
at least 40 tokens/sec/user **on the same request**. This is different from
run-level P50 acceptance. Do not treat an aggregate latency percentile as proof
that the required fraction of requests meets both constraints. Report both if
requested, and use each export's units and metric definitions across versions.

Reconcile sent, completed, failed, and deadline-cancelled requests using logs
and per-request artifacts. A completed export can show `error_summary=[]` and
`was_cancelled=false` while requests were cancelled at the duration deadline;
those unfinished requests can be absent from completed-request metrics. Report
them explicitly and check metric coverage. One-token responses may also lack
a TPOT sample. Use exported rate denominators: the observation window can
include drain/cancellation handling, so dividing totals by the requested
benchmark duration need not reproduce the reported rates.

## Memory and comparison controls

Record usable GPU KV capacity from the actual engine layout, not configured
cache fraction alone. For each independent DP replica with unsharded logical
blocks, usable tokens are `(num_gpu_blocks - num_reserved_gpu_blocks) *
block_size`; sum independent DP capacities, without multiplying by TP or EP
again. For DCP or other sharded layouts, establish the branch's logical block
semantics before applying any scaling. Host KV-store capacity is separate.

Use representative peak input-plus-output lengths, prefix sharing, block
rounding, retained cache, and imbalance when estimating feasible concurrency.
Cache capacity does not predict latency SLOs. Larger cache fractions also leave
less memory for transient prefill/MoE work; record warmup OOMs as failed trials.
Keep topology, routing/store settings, MTP, quantization, warmup, and workload
fixed for attribution, and follow the parent skill's repeated-trial policy.
