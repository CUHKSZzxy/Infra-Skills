---
name: benchmark-accuracy
description: Use when measuring local LMDeploy model or API correctness with deterministic requests, GSM8K, MMLU-Pro, OCRBench, or another small real-dataset pass; use benchmark-efficiency instead when serving speed is the primary result.
---

# Benchmark Accuracy

Use this for model/API quality checks where the main result is correctness, not
throughput, TTFT, TPOT, or concurrency. Pair with `benchmark-efficiency`
only when you also need serving speed logs for the same model/config.

## Workflow

1. Create the run folder under the current source checkout's `benchmark/`
   directory. Follow `../../docs/conventions/benchmark-artifacts.md` for
   naming, summary, and artifact subfolder layout. If the user names a desired
   destination or run folder, put the benchmark folder there and state that path
   before long runs.
   Create `context/` immediately; it is required even for quick route checks.
2. Save deployment context under `$RUN_DIR/context/` before reporting results.
   Follow `../../docs/conventions/deployment-context.md`. Use
   `scripts/capture_context.sh` for local runs. Manually fill only
   benchmark-critical gaps; leave stable or inaccessible machine/runtime fields
   as `unknown` or `null`. For accuracy, make sure the context captures task
   name, built-in mini versus real data, dataset path/split, start offset,
   few-shot count, example count, prompt/answer extraction rule, generation
   settings, request threads, timeout, extra request body, accuracy threshold,
   and allowed request or parser errors.
3. Keep decoding deterministic for quick comparisons: `temperature=0`, stable
   `top_p`, and fixed `max_tokens`.
4. Run the smallest route check first. Move to a real dataset file only after the
   server route and answer extraction are working.
5. For local server benchmarks, save the server stdout/stderr under
   `serve_logs/`, usually with `2>&1 | tee serve_logs/<label>_serve.log`,
   before running clients. Keep accuracy client stdout/stderr, JSON/JSONL/TSV
   results, response samples, endpoint probes, and parser outputs under
   `accuracy/`. Use `analysis/` only for derived summaries or post-hoc scripts.
6. Treat tiny quick-check accuracy as a regression signal only. For conclusions,
   run enough real examples for the model and dataset.
7. Finish by writing `summary.md` in the benchmark folder. Keep it short, but
   include the model/config, commands, dataset, deployment-context path,
   accuracy, request/server errors, artifact paths, fixes made, and caveats. If
   server logs were not captured, say so explicitly. Put key result data in
   Markdown tables near the top, before config and command details, so accuracy
   variants are easy to compare at a glance. The final response must include
   the run folder, exact `summary.md` path, and exact
   `context/deployment_context.md` path.

## Bundled Scripts

Copy or invoke scripts from `scripts/`:

- `capture_context.sh`: create `$RUN_DIR/context/` and its `commands/` folder
  for local deployment-context capture.
- `gsm8k_acc.py`: numeric-answer accuracy; use `--mini` for a route check or
  `--data-path` for local JSONL with `question` and `answer`.
- `mmlu_pro_acc.py`: MMLU-Pro letter accuracy; use `--mini` for a route check
  or `--data-path` for local records with `question`, `options`, `answer`, and
  optional `category`. Scores deterministic `ANSWER: <LETTER>` extraction.
- `ocrbench_acc.py`: OCRBench VLM accuracy from VLMEvalKit-style TSV, sending
  images as OpenAI `image_url` data URIs and reporting `request_errors`.

Use `--mini` first, then pass `--data-path` or the script's dataset source for
the real run. Typical setup:

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/conventions/machines.md}"
SKILL_DIR="$INFRA_SKILLS_HOME/skills/benchmark-accuracy"
RUN_DATE=${RUN_DATE:-$(date +%Y%m%d)}
RUN_DIR="./benchmark/${RUN_DATE}_${MODEL_ABBR}_<dataset>"
mkdir -p "$RUN_DIR"/{context,accuracy,serve_logs}
bash "$SKILL_DIR/scripts/capture_context.sh" "$RUN_DIR" "${LMDEPLOY_DEV_SOURCE:-$(pwd)}"

python "$SKILL_DIR/scripts/<dataset>_acc.py" --help
```

GSM8K and MMLU-Pro use text requests; OCRBench sends image files as OpenAI
`image_url` data URIs. Keep client stdout/stderr beside the JSON result, for
example:

```bash
CMD=(python "$SKILL_DIR/scripts/mmlu_pro_acc.py" \
  --base-url http://127.0.0.1:23334/v1 \
  --model "$MODEL_ABBR" \
  --num-examples 200 \
  --dump-json "$RUN_DIR/accuracy/mmlu_pro_acc.json")
printf '%q ' "${CMD[@]}" > "$RUN_DIR/context/commands/mmlu_pro_acc.cmd"
printf '\n' >> "$RUN_DIR/context/commands/mmlu_pro_acc.cmd"
"${CMD[@]}" 2>&1 | tee "$RUN_DIR/accuracy/mmlu_pro_acc.client.log"
```

## Acceptance

Before reporting accuracy, include:

- `context/deployment_context.md` captured before result reporting,
- exact server/client commands, dataset source/path, example count, and answer
  extraction rule,
- result table covering accuracy, correct/total, errors, failures, and artifact
  paths,
- server/client log paths, or explicit notes that they were not captured,
- run folder, exact `summary.md` path, and exact deployment-context path.
