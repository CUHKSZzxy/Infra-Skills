# EvalScope Serving Benchmarks

## Setup and workload choice

These commands were checked against the locally installed EvalScope 1.9.1
source. Record the actual client version and any source changes; check
`evalscope perf --help` when using another version. Use a separate client
environment and the server model's tokenizer. Dataset preparation can consume
substantial CPU/RAM and precedes serving measurement.

Set these variables in the run-local configuration:

- `EVALSCOPE_BIN`: executable from the selected client environment.
- `BENCH_BASE_URL`: OpenAI-compatible base URL ending in `/v1`.
- `MODEL_NAME`: served model name returned by `/v1/models`.
- `TOKENIZER_PATH`: tokenizer directory matching the served checkpoint.
- `RUN_DIR`: artifact directory; `TRIAL_LABEL`: unique variant/trial label.
- `MODELSCOPE_HOME` / `MODELSCOPE_CACHE`: optional local dataset cache locations.

Record the server command, model/weight dtype, KV dtype, TP/DP/EP/DCP, MTP,
prefix caching, batch/prefill limits, session length, and cache fraction using
the parent skill's deployment-context workflow. Wait for server readiness and
check the model name. A smoke request populates cache: use an unrelated prompt
or restart afterward if the contract requires an empty cache. Configure proxy
bypass for the actual endpoint host in both `NO_PROXY` and `no_proxy`.

## Live SWE-Smith example

This example requests 16 conversations of five turns: approximately 16,384
first-turn user tokens, 2,048 new user tokens per later turn, and up to 1,024
output tokens per request. The lengths are workload parameters, not universal
recommendations. Ensure the server can fit the growing history plus output.

```bash
set -euo pipefail
: "${EVALSCOPE_BIN:?}" "${BENCH_BASE_URL:?}" "${MODEL_NAME:?}"
: "${TOKENIZER_PATH:?}" "${RUN_DIR:?}" "${TRIAL_LABEL:?}"
mkdir -p "$RUN_DIR/context/commands" "$RUN_DIR/bench_logs/$TRIAL_LABEL"
cmd=("$EVALSCOPE_BIN" perf
  --model "$MODEL_NAME" --url "$BENCH_BASE_URL" --api openai
  --dataset swe_smith --tokenizer-path "$TOKENIZER_PATH"
  --multi-turn --min-turns 5 --max-turns 5
  --multi-turn-args '{"first_turn_length":16384,"subsequent_turn_length":2048}'
  --num-workers 1
  --max-tokens 1024 --extra-args '{"ignore_eos":true}'
  --number 16 --parallel 16 --rate 16 --seed 1024
  --warmup-num 0
  --outputs-dir "$RUN_DIR/bench_logs/$TRIAL_LABEL/results")
printf '%q ' "${cmd[@]}" > "$RUN_DIR/context/commands/${TRIAL_LABEL}_client.cmd"
printf '\n' >> "$RUN_DIR/context/commands/${TRIAL_LABEL}_client.cmd"
"${cmd[@]}" 2>&1 | tee "$RUN_DIR/bench_logs/$TRIAL_LABEL/evalscope.log"
```

In this version, streaming defaults to true and temperature to zero. Check
these in the saved arguments. Use top-level `--num-workers`; nested
`num_workers` in `--multi-turn-args` remains a deprecated alias, used when the
top-level option is not explicitly set. The original workflow uses the still-supported
`--multi-turn-args`; this version marks it deprecated in favor of
`--dataset-args`. Preserve the recorded command for reproduction, and check
compatibility before migrating a new workflow.

Live mode intentionally omits `--dataset-path`. It loads the SWE-Smith `tool`
split, filters and samples trajectories, and constructs turns with the chosen
tokenizer. Record dataset revision/cache provenance, seed, and client version;
a seed alone does not establish identical samples across implementations.

## Prebuilt mode

For repeatable inputs or offline reuse, replace the live construction options
(`--min-turns`, `--max-turns`, `--multi-turn-args`, `--num-workers`) with
`--dataset-path "$DATASET_PATH"`; keep `--dataset swe_smith --multi-turn`.
The file controls the turn count and lengths. Record its checksum and builder
version. Do not switch a requested live workload to prebuilt mode implicitly.

The JSON schema has a top-level `conversations` list. Each conversation is a
list of turns, each containing `messages` with only that turn's new user
messages and optional `prompt_tokens` metadata. The harness accumulates history
and inserts actual server responses; supplying full history in every turn
would duplicate it. Source assistant responses are not replayed as model output.

For a local Parquet builder, read the `messages` column from the `tool` split,
normalize messages with the matching EvalScope implementation, apply the
selected tokenizer/length/turn policy, and fail if insufficient conversations
are built. Retain the actual dataset revision, generation parameters, and
checksum. Helpers such as `_extract_messages` and `_build_conversation` are
private APIs: pin their source version if using them. A local shard sampler
and live construction need not select identical conversations even with the
same seed. Precomputed prompt counts exclude future generated responses and
are not the final server input lengths.

## Read results and compare

- Retain `benchmark_args.json`, `benchmark_summary.json`, client logs, and
  per-request artifacts under each trial's results directory. Inspect nested
  output directories instead of assuming the JSON is at the root.
- Here `--number 16` counts conversations: five successful turns each yield
  80 successful requests. Report actual success/failure and turn counts.
  Keep concurrency and arrival-rate settings distinct.
- Check actual input/output tokens, TTFT, TPOT/inter-token latency, end-to-end
  latency, request throughput, and output-token throughput, including units
  and percentiles. With `ignore_eos=true`, verify the requested output length
  was reached; context limits or failures can still shorten responses.
- Preserve live/prebuilt mode, streaming, warmup, seed, tokenizer, and cache
  policy across variants. Do not add prompt nonces to a supplied workload just
  to force cache misses. Use fresh servers for the declared cold-cache case;
  use the same explicit warmup for steady-state comparisons.
- Run at least three trials per variant for performance claims and alternate
  order. Separate dataset preparation and startup time from exported serving
  measurement time. Report incomplete trials instead of averaging them into
  successful throughput results.
