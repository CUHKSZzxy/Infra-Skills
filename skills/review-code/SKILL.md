---
name: review-code
description: Use when reviewing a current diff, PR, patch, or local changes for bugs, regressions, missing tests, maintainability risks, or LMDeploy maintainer-style feedback.
---

# Review Code

Default to a normal code-review stance: findings first, ordered by severity,
with file/line references and concrete failure modes. Review the user's current
changes unless they name a PR, branch, patch, or wider scope.

## Scope

Start with:

```bash
git status --short
git diff HEAD
git ls-files --others --exclude-standard
```

`git diff HEAD` covers staged and unstaged tracked changes, but not untracked
files. Read relevant untracked files explicitly. For a PR or branch review,
compare `HEAD` with the merge base of the target branch.

Read enough surrounding code, callers, tests, and relevant convention docs to
understand ownership and change cost. Use history only when intent or whether
debt is pre-existing remains unclear.

## Review Flow

1. Summarize changed behavior and touched ownership boundaries.
2. Read [references/code-smell-catalog.md](references/code-smell-catalog.md)
   and run the mandatory maintainability/code-smell pass alongside the normal
   review.
3. Inspect correctness, API compatibility, runtime/performance risk, tests, and
   code smells. Correctness, API, and runtime regressions outrank style, but the
   review is incomplete until the code-smell pass is done.
4. Report only actionable findings backed by exact evidence. Explain the
   failure mode and the smallest reasonable correction.
5. If no issues are found, say so clearly and note residual test or benchmark
   gaps.
6. Unless the user asks for fixes, stop after the review.

## Evidence

Code-smell review is mandatory. Treat the catalog as search guidance, not
proof. A finding must show concrete comprehension, coupling, duplication, or
change cost introduced or materially worsened by the change.

Load LMDeploy corpus evidence only for an LMDeploy PR, diff, patch, or
maintainer-style review:
[references/lmdeploy-corpus-summary.md](references/lmdeploy-corpus-summary.md)

For LMDeploy reviews, query the human review corpus instead of loading the gzip
file directly:

```bash
python3 skills/review-code/scripts/query_lmdeploy_review_corpus.py \
  --path lmdeploy/pytorch --category correctness --limit 8

python3 skills/review-code/scripts/query_lmdeploy_review_corpus.py \
  --query cuda --limit 5
```

Prefer corpus examples from the same subsystem over broad keyword matches, and
use them to sharpen the current review rather than forcing old comments onto a
new patch. Do not invent a corpus precedent.

Regenerate the corpus only when the user asks to refresh the evidence:

```bash
python3 skills/review-code/scripts/collect_lmdeploy_review_corpus.py \
  --repo InternLM/lmdeploy \
  --start-date 2026-01-01 \
  --out-dir skills/review-code/references
```

## LMDeploy Review Heuristics

When reviewing LMDeploy, prioritize recurring maintainer concerns:

- model, quantization, tokenizer/chat-template, VLM, and backend contracts;
- OpenAI-compatible API, Response API, CLI flags, and public pipeline behavior;
- PyTorch/TurboMind ownership boundaries and lifecycle compatibility;
- KV/cache accounting, CUDA graph assumptions, rank/worker behavior, async
  abort/end semantics, and backend fallback behavior;
- targeted tests, CI, benchmark evidence, docs/examples parity, and clear
  motivation for new arguments or helpers.

## Output

Put findings first. Use this shape when useful:

```text
[medium] path/to/file.py:123 - Short issue title
Failure mode: ...
Smallest correction: ...
```

Keep open questions, test gaps, corpus queries used, and summaries after the
findings. Keep code-smell findings separate from correctness, API, performance,
or LMDeploy maintainer-policy findings.
