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
   directory. Follow `../../docs/local-conventions.md` for naming, summary, and
   artifact subfolder layout. If the user names a desired destination or run
   folder, put the benchmark folder there and state that path before long runs.
2. Record the model alias, server URL, backend, quantization/KV-cache settings,
   dataset path or built-in quick-check set, number of shots, number of
   examples, and generation settings.
3. Keep decoding deterministic for quick comparisons: `temperature=0`, stable
   `top_p`, and fixed `max_tokens`.
4. Run the smallest route check first. Move to a real dataset file only after the
   server route and answer extraction are working.
5. For local server benchmarks, save the server stdout/stderr under
   `serve_logs/`, usually with `2>&1 | tee serve_logs/<label>_serve.log`,
   before running clients. Keep client stdout/stderr and JSON results under
   `accuracy/` or `eval_logs/` when comparing variants.
6. Treat tiny quick-check accuracy as a regression signal only. For conclusions,
   run enough real examples for the model and dataset.
7. Finish by writing `summary.md` in the benchmark folder. Keep it short, but
   include the model/config, commands, dataset, accuracy, request/server errors,
   artifact paths, fixes made, and caveats. If server logs were not captured,
   say so explicitly. Put key result data in Markdown tables near the top,
   before config and command details, so accuracy variants are easy to compare
   at a glance. The final response must include the run folder and exact
   `summary.md` path.

## Bundled Scripts

Copy or invoke scripts from `scripts/`:

- `gsm8k_acc.py`: numeric-answer accuracy; use `--mini` for a route check or
  `--data-path` for local JSONL with `question` and `answer`.
- `mmlu_pro_acc.py`: MMLU-Pro letter accuracy; use `--mini` for a route check
  or `--data-path` for local records with `question`, `options`, `answer`, and
  optional `category`. Scores deterministic `ANSWER: <LETTER>` extraction.
- `ocrbench_acc.py`: OCRBench VLM accuracy from VLMEvalKit-style TSV, sending
  images as OpenAI `image_url` data URIs and reporting `request_errors`.

Examples assume:

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/local-conventions.md}"
SKILL_DIR="$INFRA_SKILLS_HOME/skills/benchmark-accuracy"
RUN_DATE=${RUN_DATE:-$(date +%Y%m%d)}
```

GSM8K:

```bash
RUN_DIR="./benchmark/${RUN_DATE}_${MODEL_ABBR}_gsm8k"
mkdir -p "$RUN_DIR/accuracy"

python "$SKILL_DIR/scripts/gsm8k_acc.py" \
  --base-url http://127.0.0.1:23334/v1 \
  --model "$MODEL_ABBR" \
  --num-shots 5 \
  --dump-json "$RUN_DIR/accuracy/gsm8k_acc.json"
```

MMLU-Pro:

```bash
RUN_DIR="./benchmark/${RUN_DATE}_${MODEL_ABBR}_mmlu_pro"
mkdir -p "$RUN_DIR/accuracy"

python "$SKILL_DIR/scripts/mmlu_pro_acc.py" \
  --base-url http://127.0.0.1:23334/v1 \
  --model "$MODEL_ABBR" \
  --num-examples 200 \
  --dump-json "$RUN_DIR/accuracy/mmlu_pro_acc.json" \
  2>&1 | tee "$RUN_DIR/accuracy/mmlu_pro_acc.client.log"
```

OCRBench:

```bash
RUN_DIR="./benchmark/${RUN_DATE}_${MODEL_ABBR}_ocrbench"
mkdir -p "$RUN_DIR/accuracy"

python "$SKILL_DIR/scripts/ocrbench_acc.py" \
  --base-url http://127.0.0.1:23333/v1 \
  --model "$MODEL_ABBR" \
  --data-path /path/to/OCRBench.tsv \
  --dump-json "$RUN_DIR/accuracy/ocrbench_acc.json" \
  2>&1 | tee "$RUN_DIR/accuracy/ocrbench_acc.client.log"
```

## Acceptance

Before reporting accuracy, include:

- exact server/client commands, dataset source/path, example count, and answer
  extraction rule,
- result table covering accuracy, correct/total, errors, failures, and artifact
  paths,
- server/client log paths, or explicit notes that they were not captured,
- run folder and exact `summary.md` path.
