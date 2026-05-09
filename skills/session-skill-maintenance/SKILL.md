---
name: session-skill-maintenance
description: Use when a task, debug session, PR fix, or study session has just completed and the user asks whether reusable skills, workflow guidance, or skill repo updates should be summarized or applied.
---

# Session Skill Maintenance

Use this at the end of a meaningful work session to decide whether the lesson
should become reusable skill guidance. Optimize for the user's preference:
concise, operational, repo-aware, and easy to remove if it stops being useful.

This skill is the compression gate for the repo's heuristic-learning loop. Use
`docs/heuristic-learning.md` for boundaries, and use
`templates/lesson-candidate.md` as a temporary scratchpad when the promotion
decision is not obvious.

## 1. Decide Whether Anything Belongs In Skills

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

## 2. Prefer Small Updates

Choose the smallest durable form:

1. update an existing skill if the lesson fits its trigger
2. add a short section or bullet before creating a new skill
3. create a new skill only if the trigger is distinct and likely to recur
4. add a reference only when the detail is useful but too long for `SKILL.md`
5. add a script only when deterministic reuse beats retyping commands
6. update model PR history when the lesson belongs to a model family
7. avoid bundled references/scripts unless deterministic reuse needs them

If the skill might consume context without clear value, say so and skip it.

## 3. Write Trigger-First Skills

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

## 4. Keep The Skill Repo Aligned

When changing skills in `/nvme1/zhouxinyu/Infra-Skills`:

- update `README.md` if the skill list, trigger, or behavior changes
- stage only intended skill files
- preserve `.codex/skills/.system`; custom skills are additive
- expose repo skills by symlink, not copy, when applying locally
- run the linker after adding/removing a skill:

```bash
scripts/link_skills.sh
```

If Codex skill-home writes hit sandbox restrictions, rerun the linker with the
available write-capable path or approval rather than leaving a partial link.

## 5. Validate And Report

Run the narrow validation for changed skill docs:

```bash
/nvme1/zhouxinyu/miniconda3/envs/infra-skills/bin/pre-commit run --files <changed-files>
```

After adding a skill, verify local symlinks when possible:

```bash
readlink /nvme1/zhouxinyu/.codex/skills/<skill-name>
readlink /nvme1/zhouxinyu/.claude/skills/<skill-name>
```

Report:

- what skill was added or updated
- why it is reusable
- validation result
- whether it was linked locally
- whether changes are committed or still local
