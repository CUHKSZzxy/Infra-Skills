---
name: engineering-guardrails
description: Use when applying workspace coding preferences or planning shared-GPU work.
---

# Workspace Engineering Preferences

- Use the fewest GPUs the workload needs; an all-GPU reservation requires an
  explicit request. Do not run parallel measurements on the same GPU.
- Prefer explicit inputs/results, private helpers, composition, and keywords
  for non-obvious arguments. Existing subsystem conventions take precedence.
- Avoid speculative compatibility paths and guards without a concrete failure
  mode. Keep unrelated style changes out of the patch.

Continue through the requested result and its relevant validation. After checks
pass, broaden testing only for new failures or unresolved concerns. Keep reports
concise: outcome, supporting evidence, and material gaps.
