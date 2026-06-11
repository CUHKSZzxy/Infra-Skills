---
name: lmdeploy-humanize-review
description: "Use when reviewing LMDeploy PRs, diffs, patches, or local changes in the style of human maintainers by consulting the 2026 human PR review corpus, excluding Copilot, bots, and coding-agent comments."
---

# LMDeploy Humanize Review

## Overview

Use this skill when the user asks for a human-style LMDeploy review or wants
feedback that resembles LMDeploy maintainers instead of generic linting.

The bundled corpus was collected from `InternLM/lmdeploy` PRs created since
2026-01-01, excluding PRs or review comments from GitHub bots, Copilot, and
obvious coding-agent accounts. It contains 421 inline review threads and 533
human reviewer comments. The collector saw and filtered 1,115 agent reviewer
comments on the target PRs.

Read [references/corpus-summary.md](references/corpus-summary.md) first for
coverage, counts, top paths, reviewers, and category distribution. Do not load
the gzip corpus directly into context; query it with the helper script.

## Corpus Tools

Search by topic, path, category, or reviewer:

```bash
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py \
  --query cuda --limit 5

python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py \
  --path lmdeploy/pytorch --category correctness --limit 8

python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py \
  --query turbomind --format jsonl --limit 3
```

The full corpus is:

```text
references/lmdeploy-review-corpus-2026.jsonl.gz
```

Regenerate it only when the user asks to refresh the evidence:

```bash
HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 \
python3 skills/lmdeploy-humanize-review/scripts/collect_lmdeploy_review_corpus.py \
  --repo InternLM/lmdeploy \
  --start-date 2026-01-01 \
  --out-dir skills/lmdeploy-humanize-review/references
```

Drop the proxy variables when GitHub API access works directly.

## Review Workflow

1. Inspect the actual diff first.
   - Use `git diff`, `gh pr diff`, or the patch supplied by the user.
   - Identify touched LMDeploy surfaces: OpenAI serving, Response API,
     pipeline, `AsyncEngine`, PyTorch engine, TurboMind, model support, VLM,
     quantization, speculative decoding, CUDA/Triton kernels, docs, tests, or
     workflows.
2. Read `references/corpus-summary.md`.
   - Note top review surfaces and categories that overlap with the diff.
   - Preserve original language for relevant corpus examples.
3. Query similar review threads.
   - Search by touched path first.
   - Search by risk keyword next, for example `api_server`, `responses`,
     `AsyncEngine`, `pipeline`, `Session`, `turbomind`, `pytorch`, `kv`,
     `cuda`, `graph_runner`, `spec_decode`, `awq`, `qwen`, `vl`, `benchmark`,
     or `workflow`.
   - Prefer evidence from the same subsystem over broad keyword matches.
4. Produce a review response.
   - Lead with concrete findings ordered by severity.
   - Include file and line references from the reviewed diff.
   - Explain the failure mode or compatibility risk, not just style preference.
   - Suggest a fix or validation step when actionable.
   - Keep nits separate from correctness, API, performance, or runtime risks.
5. If no issue is found, say so clearly.
   - Mention residual risk and the targeted test or benchmark that would raise
     confidence.

## LMDeploy Review Heuristics From The Corpus

Prioritize these risks because they recur heavily in the 2026 human review
threads:

- **Model, quantization, and backend contracts**: model config defaults,
  tokenizer/chat-template behavior, AWQ/FP8/INT4 paths, speculative decoding,
  VLM preprocessing, dtype/shape assumptions, and PyTorch/TurboMind parity.
- **Serving and API compatibility**: OpenAI-compatible endpoints, Response API,
  CLI flags, public pipeline behavior, generated OpenAPI docs, deprecation
  paths, and backward compatibility for third-party `AsyncEngine` users.
- **PyTorch/TurboMind boundaries**: avoid leaking serving code into backend
  internals, reusing helpers across the wrong ownership boundary, or changing
  event-loop/session lifecycle contracts without a migration story.
- **Correctness before cleanup**: reviewers often ask about exact caller
  responsibility, wrong argument types, tensor shape mismatches, session object
  versus session id confusion, and edge cases in guided/speculative decoding.
- **Tests, CI, and benchmark evidence**: add targeted tests for behavior
  changes, avoid duplicate workflow dependency pins, justify benchmark script
  changes, and provide benchmark evidence for performance claims or hot paths.
- **Memory, cache, distributed, and GPU runtime**: check KV/cache accounting,
  block offsets, CUDA graph assumptions, rank/worker behavior, async abort/end
  semantics, and backend-specific fallback behavior.
- **Docs and examples**: keep English and Chinese docs aligned with removed
  CLI/chat-template behavior, OpenAPI rendering, docstring standards, endpoint
  names, model support, and version-specific setup.
- **Maintainability**: question unnecessary new arguments, duplicate helpers,
  broad refactors, typo-prone names, and changes whose motivation is not clear.

## Review Style

Mirror human LMDeploy review habits:

- Be terse and specific.
- Prefer a question when motivation or ownership is ambiguous.
- Call out public API, serving, or backend behavior changes explicitly.
- Do not invent a corpus precedent; query the corpus when using it as evidence.
- Keep multilingual comments intact. Answer in the user's language unless they
  ask otherwise.
- Use corpus examples to sharpen the current review, not to force a patch into
  an old template.

## Output Contract

For a normal review, return:

- Findings first, ordered by severity, with file/line references.
- Open questions or assumptions.
- Test or benchmark gaps.
- A short summary only after findings.

For a review-prep pass before the user opens a PR, return:

- likely reviewer concerns
- missing tests or benchmark evidence
- suggested patch cleanup
- corpus queries used

For a corpus-backed explanation, include the query terms and summarize the
matched review behavior without dumping long comment bodies.
