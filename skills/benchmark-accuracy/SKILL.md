---
name: benchmark-accuracy
description: Use when measuring LMDeploy model or API accuracy with deterministic requests or real datasets.
---

# Benchmark Accuracy

Use this for model/API quality checks where the main result is correctness, not
throughput, TTFT, TPOT, or concurrency. Pair with `benchmark-efficiency`
only when you also need serving speed logs for the same model/config.

## Measurement Contract

Use [artifact conventions](../../docs/conventions/benchmark-artifacts.md) for
the run directory and logs, honoring a user-provided destination. Capture
[deployment context](../../docs/conventions/deployment-context.md) with
`scripts/capture_context.sh` before reporting accuracy. Keep quick route checks
in the same run record; they are regression signals, not dataset conclusions.

Record accuracy-specific fields: mini versus real data, split and offset,
few-shot count, example count, prompt/answer extraction rule, generation
settings, request threads, timeout, extra request body, accuracy threshold, and
allowed request/parser errors. Fill only benchmark-critical context gaps;
leave unavailable facts as `unknown` or `null`.

Use deterministic decoding for comparisons: `temperature=0`, stable `top_p`,
and fixed `max_tokens`. Verify the route and answer parser with a mini check
unless already established for this configuration, then use enough real
examples to support the requested conclusion.

Save server stdout/stderr under `serve_logs/` when launching a local server.
Keep client logs, results, response samples, and parser outputs under
`accuracy/`; use `analysis/` for derived summaries only.

## Bundled Scripts

Run the bundled clients with `--help` for dataset and request options:

- `scripts/gsm8k_acc.py`: numeric-answer scoring from local JSONL
  (`question`, `answer`); `--mini` checks route/parser behavior.
- `scripts/mmlu_pro_acc.py`: deterministic `ANSWER: <LETTER>` extraction from
  records with `question`, `options`, `answer`, and optional `category`;
  `--mini` is available.
- `scripts/ocrbench_acc.py`: VLMEvalKit-style TSV; sends OpenAI `image_url` data
  URIs and reports request errors separately.
- `scripts/capture_context.sh`: captures local deployment metadata and creates
  `context/commands/`.

Use explicit `--data-path` or the client's dataset source for a real run.
Keep client stdout/stderr beside the result JSON. Resolve script paths from
`INFRA_SKILLS_HOME` in [machine conventions](../../docs/conventions/machines.md).

## Result

Write `summary.md` with a result table (accuracy, correct/total, and errors),
model/config, dataset and extraction policy, exact commands, artifact paths,
fixes, and caveats. State when server/client logs could not be captured. Include
the run folder, summary path, and `context/deployment_context.md` path in the
final response, following artifact conventions.
