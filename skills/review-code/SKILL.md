---
name: review-code
description: Use when reviewing LMDeploy changes against backend contracts or maintainer conventions.
---

# LMDeploy Review Evidence

Use this for LMDeploy-specific review context. Ordinary code review does not
need a separate tutorial or smell-catalog pass.

Relevant contracts depend on the diff: model/quantization and VLM preprocessing,
public APIs/CLI, PyTorch/TurboMind ownership, KV accounting, CUDA graphs, worker
lifecycle, async abort/end, and fallback behavior. Load an implementation skill
only when the affected contract is unclear.

When maintainer precedent would resolve a question, query the human corpus:

```bash
python3 "$INFRA_SKILLS_HOME/skills/review-code/scripts/query_lmdeploy_review_corpus.py" \
  --path lmdeploy/pytorch --category correctness --limit 8
```

Resolve `INFRA_SKILLS_HOME` from
[machine conventions](../../docs/conventions/machines.md) if needed.
Use the [corpus summary](references/lmdeploy-corpus-summary.md) for coverage and
query examples; the full gzip is not intended for prompt context. Historical
comments are evidence about their original patches, not universal requirements.
Refresh the corpus only when requested with `scripts/collect_lmdeploy_review_corpus.py`.

Report concrete regressions and introduced maintenance costs, with locations
and failure modes. A review-only request ends with findings; requested fixes
continue through affected validation.
