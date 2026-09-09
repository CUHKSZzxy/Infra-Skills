# Heuristic Learning Framework

This repo is the small heuristic-learning layer for recurring LMDeploy work.
It should preserve lessons that make future agent runs more reliable, while
keeping raw session history out of the active skill context.

## Loop

When a session yields a candidate lesson, use this loop:

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

- `skills/*/SKILL.md`: precise triggers, essential constraints, completion
  criteria, and routes to task-specific detail.
- `skills/*/references/`: longer examples, file maps, pitfalls, and background
  that should only load after a specific skill step needs it.
- `skills/*/scripts/`: deterministic helpers that are safer to run than
  retyping commands or benchmark snippets.
- `docs/conventions/*.md`: machine paths, environment setup, linking behavior,
  and benchmark artifact layout.
- rollout summaries and memory: raw session history, exact logs, private paths,
  and facts that are useful but not worth loading as skills.

Do not promote:

- one-off logs or private request payloads;
- generic advice the agent already knows;
- broad rules that would trigger too often;
- examples longer than the rule they teach;
- local-machine facts unless they clearly belong in
  `docs/conventions/machines.md`.

## Promotion Choices

When a lesson candidate is useful, choose one:

- **Update a skill** when it changes what the agent should do.
- **Add a reference** when the lesson is detailed but only needed after a skill
  is already active.
- **Add a script** when the same mechanical check or benchmark should be reused.
- **Defer** when the lesson might recur but has not proved reusable yet.
- **Reject** when the candidate is too narrow, stale, private, or expensive in
  context.

Prefer updating existing files over creating new skills. A new skill needs a
distinct trigger, repeated value, and low context cost.

If the decision is unclear, use a temporary five-field scratchpad: symptom,
root cause, reusable rule, target home, and validation. Do not keep the
scratchpad after the lesson is promoted, deferred, or rejected.

## Compression Checks

Periodically review the repo for accumulated complexity:

- Are two skills overlapping?
- Is a trigger too broad or too narrow?
- Did a reference become stale after an LMDeploy API change?
- Can a repeated rule be removed or mechanics moved into an existing helper?
- Does a mandatory step still protect a concrete contract, or can it be conditional?
- Does publishing permission cover these changes, rather than an already-completed push?
- Is the completion condition tied to the requested outcome and evidence?
- Does guidance apply across the models using this repo, without stale model labels?
- Does it preserve domain knowledge instead of coaching basic model capabilities?
- Did a rule help in later sessions, or should it be deleted?
- Does README still match the real skill behavior?

Healthy heuristic learning means absorbing feedback and compressing history.
Only adding rules is not enough.

## Validation

For changed docs or skills, run the narrow validation command from
`docs/conventions/environments.md`. When skills are added or removed, follow
`docs/conventions/linking.md` and verify the local symlinks if possible.
