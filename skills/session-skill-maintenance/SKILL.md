---
name: session-skill-maintenance
description: Use when a task, debug session, PR fix, or study session has just completed and the user asks whether reusable skills, workflow guidance, or skill repo updates should be summarized or applied.
---

# Session Skill Maintenance

Use this at the end of a meaningful work session to decide whether the lesson
should become reusable skill guidance. Optimize for the user's preference:
concise, operational, repo-aware, and easy to remove if it stops being useful.

This skill is the compression gate for the repo's heuristic-learning loop. Use
`docs/heuristic-learning.md` as the canonical policy. Use
`templates/lesson-candidate.md` only when the promotion decision is not obvious.

## 1. Decide Whether Anything Belongs

Add or update skill guidance only when the session produced a pattern likely to
recur.

Good candidates:

- a debugging workflow that found root cause, not just a one-off fix
- a PR/update workflow that avoided a local-tool or branch trap
- a validation pattern the user explicitly prefers
- a repo convention that future agents should follow
- a compact decision rule that would have prevented confusion

Poor candidates:

- private prompts, request payloads, model paths, logs, or local data
- details that only explain this single session
- generic engineering advice Codex already knows
- broad skills that would trigger too often
- examples that are longer than the rule they teach

## 2. Choose The Smallest Home

Use the promotion choices in `docs/heuristic-learning.md`. Prefer updating an
existing file over adding a new skill. If the lesson might consume context
without clear value, say so and skip it.

## 3. Write Trigger-First Skills When Needed

Frontmatter description should answer "when should an agent load this?"

Use:

```yaml
description: Use when [specific symptoms or task conditions]
```

Avoid:

- workflow summaries in the description
- vague names like `debugging`
- personal session narratives
- over-specific triggers such as one endpoint, one file, or one prompt

Body style:

- keep it concise and operational
- list steps in the order an agent should do them
- include commands only when they are reusable
- state what not to do when that prevents repeated mistakes
- keep local machine assumptions explicit and scoped

## 4. Keep The Repo Aligned

Use local paths and envs from `docs/local-conventions.md`.

When changing skills:

- update `README.md` if the visible skill list or one-line index changes
- stage only intended skill files
- expose repo skills by symlink, not copy, when applying locally
- run the linker after adding/removing a skill or changing local symlink targets:

```bash
scripts/link_skills.sh
```

Docs-only edits to existing skills do not need relinking when the existing
symlink already points at this repo. If Codex skill-home writes hit sandbox
restrictions, rerun the linker with the available write-capable path or approval
rather than leaving a partial link.

## 5. Validate And Report

Run the narrow validation command from `docs/local-conventions.md`.

Report:

- what skill was added or updated
- why it is reusable
- validation result
- whether it was linked locally
- whether changes are committed or still local
