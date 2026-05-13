---
name: e2e-accuracy-benchmark
description: Use when running or creating quick local end-to-end accuracy checks for model/API serving systems, including OpenAI-compatible LMDeploy/vLLM/SGLang or similar endpoints, especially GSM8K-style numeric-answer smoke tests or small real-dataset accuracy passes.
---

# E2E Accuracy Benchmark

Use this for model/API quality checks where the main result is correctness, not
throughput, TTFT, TPOT, or concurrency. Pair with `e2e-efficiency-benchmark`
only when you also need serving speed logs for the same model/config.

## Workflow

1. Record the model alias, server URL, backend, quantization/KV-cache settings,
   dataset path or built-in smoke set, number of shots, number of examples, and
   generation settings.
2. Keep decoding deterministic for quick comparisons: `temperature=0`, stable
   `top_p`, and fixed `max_tokens`.
3. Run the smallest smoke first. Move to a real dataset file only after the
   server route and answer extraction are working.
4. Save JSON results beside other run artifacts when comparing variants.
5. Treat tiny smoke accuracy as a regression signal only. For conclusions, run
   enough real examples for the model and dataset.
6. Finish by writing `summary.md` in the benchmark folder. Keep it short, but
   include the model/config, commands, dataset, accuracy, request/server errors,
   artifact paths, fixes made, and caveats. Put key result data in Markdown
   tables near the top, before config and command details, so accuracy variants
   are easy to compare at a glance.

## Bundled Scripts

Copy or invoke scripts from `scripts/`:

- `gsm8k_acc.py`: GSM8K-style numeric-answer accuracy test against an
  OpenAI-compatible server. By default it downloads/caches the full GSM8K test
  JSONL; pass `--mini` only for a tiny route smoke, or `--data-path` for a
  local GSM8K-format JSONL file with `question` and `answer` fields.

Example:

```bash
python skills/e2e-accuracy-benchmark/scripts/gsm8k_acc.py \
  --base-url http://127.0.0.1:23334/v1 \
  --model "$MODEL_ABBR" \
  --num-shots 5 \
  --dump-json ./analysis/gsm8k_acc.json
```

## Acceptance

Before reporting accuracy, include:

- exact server and accuracy command,
- dataset source/path and example count,
- answer extraction rule,
- score, failed examples if any, and result JSON path if saved,
- result table covering accuracy, correct/total, errors, and artifact path,
- `summary.md` path in the benchmark folder.
