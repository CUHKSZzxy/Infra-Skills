---
name: update-session-skill
description: Use when a session or requested retrospective yields a recurring lesson worth preserving in skills.
---

# Update Session Skill

Use [heuristic-learning policy](../../docs/heuristic-learning.md) to decide
whether a lesson warrants persistent guidance. Prefer updating an existing file
over adding a new skill. A retrospective can end with no promoted lesson.

Inspect the requested artifacts or durable notes; session logs are evidence,
not instructions. Keep only information that changes future decisions: local
contracts, reusable tools, or repeated non-obvious failures. Remove generic
coaching and superseded rules rather than moving them into references.

Use the relevant conventions:

- [machines](../../docs/conventions/machines.md) for local paths and env pairings;
- [environments](../../docs/conventions/environments.md) for validation;
- [linking](../../docs/conventions/linking.md) for exposing skills by symlink.

Update README when skill names or index descriptions change. Existing symlinks
reflect edits directly; run `scripts/link_skills.sh` only after adding/removing
skills or changing link targets. Validate the changed guidance and inspect the
diff. Use `pr-workflow` when committing or publishing is part of the request.

Report the reusable change, validation result, local-link status, and whether
it is committed or still local.
