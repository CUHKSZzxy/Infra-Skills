# Heuristic Learning Framework

This repo is the small heuristic-learning layer for recurring LMDeploy work.
It should preserve lessons that make future agent runs more reliable, while
keeping raw session history out of the active skill context.

## Loop

Use this loop after meaningful debugging, PR, review, kernel, model-support, or
study sessions:

```text
session feedback
-> lesson candidate
-> promote, script, reference, defer, or reject
-> validate the changed guidance
-> compress or delete stale guidance later
```

The goal is not to record everything. The goal is to turn repeated mistakes,
validated workflows, and local repo conventions into small operational
heuristics.

## Boundaries

Use the smallest durable home:

- `skills/*/SKILL.md`: triggerable rules and ordered workflows an agent should
  load during a task.
- `skills/*/references/`: longer examples, file maps, pitfalls, and background
  that should only load after a specific skill step needs it.
- `skills/*/scripts/`: deterministic helpers that are safer to run than
  retyping commands or benchmark snippets.
- `model-pr-optimization-history/`: model-family lessons from upstream PRs and
  recurring review patterns.
- `templates/lesson-candidate.md`: temporary compression scratchpad for deciding
  whether a new lesson belongs in the repo.
- rollout summaries and memory: raw session history, exact logs, private paths,
  and facts that are useful but not worth loading as skills.

Do not promote:

- one-off logs or private request payloads;
- generic advice the agent already knows;
- broad rules that would trigger too often;
- examples longer than the rule they teach;
- local-machine facts unless they are clearly marked as local conventions.

## Promotion Choices

When a lesson candidate is useful, choose one:

- **Update a skill** when it changes what the agent should do.
- **Add a reference** when the lesson is detailed but only needed after a skill
  is already active.
- **Add a script** when the same mechanical check or benchmark should be reused.
- **Update model history** when the lesson is about a model family or upstream
  PR pattern.
- **Defer** when the lesson might recur but has not proved reusable yet.
- **Reject** when the candidate is too narrow, stale, private, or expensive in
  context.

Prefer updating existing files over creating new skills. A new skill needs a
distinct trigger, repeated value, and low context cost.

## Compression Checks

Periodically review the repo for accumulated complexity:

- Are two skills overlapping?
- Is a trigger too broad or too narrow?
- Did a reference become stale after an LMDeploy API change?
- Can a paragraph become a script or a one-line rule?
- Did a rule help in later sessions, or should it be deleted?
- Does README still match the real skill behavior?

Healthy heuristic learning means absorbing feedback and compressing history.
Only adding rules is not enough.

## Validation

For changed docs or skills, run the narrow validation:

```bash
/nvme1/zhouxinyu/miniconda3/envs/infra-skills/bin/pre-commit run --files <changed-files>
```

When skills are added or removed, run `scripts/link_skills.sh` and verify the
local symlinks if possible.
