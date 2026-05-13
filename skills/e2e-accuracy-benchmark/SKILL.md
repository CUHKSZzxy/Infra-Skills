---
name: e2e-accuracy-benchmark
description: Use when running or creating quick local end-to-end accuracy checks for model/API serving systems, including OpenAI-compatible LMDeploy/vLLM/SGLang or similar endpoints, especially GSM8K-style numeric-answer smoke tests or small real-dataset accuracy passes.
---

# E2E Accuracy Benchmark

Use this for model/API quality checks where the main result is correctness, not
throughput, TTFT, TPOT, or concurrency. Pair with `e2e-efficiency-benchmark`
only when you also need serving speed logs for the same model/config.

## Workflow

1. Create the run folder under the current source checkout's `benchmark/`
   directory, using `benchmark/e2e_<model>_<dataset-or-task>/`. Follow
   `docs/local-conventions.md` for summary and artifact subfolder layout.
2. Record the model alias, server URL, backend, quantization/KV-cache settings,
   dataset path or built-in smoke set, number of shots, number of examples, and
   generation settings.
3. Keep decoding deterministic for quick comparisons: `temperature=0`, stable
   `top_p`, and fixed `max_tokens`.
4. Run the smallest smoke first. Move to a real dataset file only after the
   server route and answer extraction are working.
5. For local server benchmarks, save the server stdout/stderr under
   `0_serve_logs/`, usually with `2>&1 | tee 0_serve_logs/<label>_serve.log`,
   before running clients. Keep client stdout/stderr and JSON results under
   `0_accuracy/` or `0_eval_logs/` when comparing variants.
6. Treat tiny smoke accuracy as a regression signal only. For conclusions, run
   enough real examples for the model and dataset.
7. Finish by writing `summary.md` in the benchmark folder. Keep it short, but
   include the model/config, commands, dataset, accuracy, request/server errors,
   artifact paths, fixes made, and caveats. If server logs were not captured,
   say so explicitly. Put key result data in Markdown tables near the top,
   before config and command details, so accuracy variants are easy to compare
   at a glance.

## Bundled Scripts

Copy or invoke scripts from `scripts/`:

- `gsm8k_acc.py`: GSM8K-style numeric-answer accuracy test against an
  OpenAI-compatible server. By default it downloads/caches the full GSM8K test
  JSONL; pass `--mini` only for a tiny route smoke, or `--data-path` for a
  local GSM8K-format JSONL file with `question` and `answer` fields.
- `ocrbench_acc.py`: OCRBench visual accuracy test against an
  OpenAI-compatible VLM server. It reads VLMEvalKit-style OCRBench TSV files
  with `index`, `image`, `question`, `answer`, and `category` fields, sends
  images as OpenAI `image_url` data URIs, and applies VLMEvalKit-style
  substring scoring by category. Use `OCRBench.tsv` for normal benchmark
  conclusions; use `OCRBench_MINI.tsv` only as a quick route smoke.

Example:

```bash
INFRA_SKILLS_HOME=${INFRA_SKILLS_HOME:-/nvme1/zhouxinyu/Infra-Skills}
SKILL_DIR="$INFRA_SKILLS_HOME/skills/e2e-accuracy-benchmark"
mkdir -p ./benchmark/e2e_qwen35_35b_gsm8k/0_accuracy

python "$SKILL_DIR/scripts/gsm8k_acc.py" \
  --base-url http://127.0.0.1:23334/v1 \
  --model "$MODEL_ABBR" \
  --num-shots 5 \
  --dump-json ./benchmark/e2e_qwen35_35b_gsm8k/0_accuracy/gsm8k_acc.json
```

```bash
INFRA_SKILLS_HOME=${INFRA_SKILLS_HOME:-/nvme1/zhouxinyu/Infra-Skills}
SKILL_DIR="$INFRA_SKILLS_HOME/skills/e2e-accuracy-benchmark"
mkdir -p ./benchmark/e2e_qwen3_omni_ocrbench/0_accuracy

python "$SKILL_DIR/scripts/ocrbench_acc.py" \
  --base-url http://127.0.0.1:23333/v1 \
  --model "$MODEL_ABBR" \
  --data-path /nvme1/zhouxinyu/LMUData/OCRBench.tsv \
  --dump-json ./benchmark/e2e_qwen3_omni_ocrbench/0_accuracy/ocrbench_acc.json \
  2>&1 | tee ./benchmark/e2e_qwen3_omni_ocrbench/0_accuracy/ocrbench_acc.client.log
```

## Acceptance

Before reporting accuracy, include:

- exact server and accuracy command,
- dataset source/path and example count,
- answer extraction rule,
- score, failed examples if any, and result JSON path if saved,
- server log path, or an explicit note that no server log was captured,
- client log path, or an explicit note that no client log was captured,
- result table covering accuracy, correct/total, errors, and artifact path,
- `summary.md` path under `benchmark/e2e_<model>_<dataset-or-task>/`.
