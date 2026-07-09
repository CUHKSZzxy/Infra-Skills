---
name: project-decomposition
description: Use when explicitly invoked to split a discussed or saved Markdown project plan into small, independently verifiable task packets for separate or parallel Codex sessions.
---

# Project Decomposition

Use this when the user manually asks to decompose a discussed plan, saved
Markdown plan, or large objective into work packets for separate Codex sessions.
The goal is to produce small modules that can be built, reviewed, tested, and
rolled back independently.

Do not use this for a tiny one-file change. For normal coding discipline, pair
with `engineering-guardrails`; this skill is for shaping the work before execution.

## Manual Trigger Workflow

The intended workflow is:

1. The user and Codex discuss the project and save a general plan in Markdown.
2. The user explicitly invokes this skill, usually with the plan path.
3. Read the plan and relevant conversation context, then produce a task split.
4. Save one coordinator Markdown file plus one task packet per independent
   session when the user asks for files.

If no output path is provided, write next to the plan in a folder named
`<plan-stem>-tasks/`. If the plan path is unknown, ask for it or produce the
decomposition in chat without writing files.

## 1. Anchor The Objective And Source Plan

Restate the target outcome in concrete terms:

- source plan path and any relevant discussion assumptions
- user-visible goal or engineering outcome
- current known constraints: repo, branch, env, time, hardware, APIs, data
- success criteria and non-goals
- assumptions that need validation

Ask only for missing information that would change the decomposition. Otherwise
state reasonable assumptions and continue.

## 2. Find Natural Boundaries

Inspect enough context to identify real boundaries before splitting work:

- user workflows or API surfaces
- dataflow and state ownership
- model/config/schema contracts
- files, packages, services, or processes that already form seams
- existing tests, logs, benchmarks, and validation hooks

Prefer boundaries that match contracts in the system, not arbitrary layers.

## 3. Cut Modules

Each module should satisfy most of these:

- one clear responsibility
- explicit in-scope and out-of-scope items
- stable input/output contract or touched file surface
- small enough for one focused implementation and review pass
- independently verifiable by a command, artifact, smoke test, diff check, or
  manual observation
- minimal coupling to other modules

Avoid modules named only by phase, such as "backend", "frontend", "testing",
or "cleanup". If a module cannot be verified by itself, split out a harness,
fixture, or discovery module first.

For parallel Codex sessions, also check:

- file ownership does not overlap unless the dependency is explicit
- each task has enough context to start without the original conversation
- each task has a clear stopping point and handoff artifact
- integration work is a separate final task when independent outputs must merge

Do not pretend tasks are parallel if they mutate the same contract or files.
Create a contract/discovery task first, then split dependent work after that.

## 4. Order The Work

Choose an execution order that reduces uncertainty:

1. discovery or contract clarification
2. thin vertical slice or minimal reproducible path
3. shared interfaces only after their callers are clear
4. highest-risk modules before broad polish
5. dependent modules after the boundary they consume
6. final integration, cleanup, and documentation

Keep refactors local to the module that proves they are needed. If a boundary
changes mid-task, update the decomposition before continuing.

For important dataflow, control flow, or interface details that would be
ambiguous in prose, include short pseudocode in the affected module's
implementation notes. Keep it minimal and non-speculative.

## 5. Define Verification

For every module, specify:

- exact check to run or artifact to inspect
- expected pass condition
- failure signal that would stop or reshape the plan
- whether the check is unit, integration, benchmark, manual, or code-review
  based

No module is "done" only because code was written. If reliable validation does
not exist yet, make validation setup its own module.

## 6. Save Task Packets

When writing files, create:

- `decomposition.md`: coordinator view, dependency graph, execution order, and
  integration notes.
- `T01-<short-name>.md`, `T02-<short-name>.md`, ...: task packets for separate
  Codex sessions.

Each task packet must be self-contained:

```markdown
# T01: <Task Name>

## Objective

## Background

## Boundary
- In scope:
- Out of scope:
- Files/contracts likely touched:
- Must not touch:

## Dependencies

## Implementation Notes

## Verification
- Command/artifact:
- Expected result:
- Failure signal:

## Handoff
- Output to produce:
- What to report back:
```

Keep task packets concise. Include enough context to start, but not the whole
original discussion.

## 7. Output Contract

Produce a concise coordinator plan in this shape:

| ID | Module | Boundary | Depends On | Verification | Done When |
| --- | --- | --- | --- | --- | --- |
| M1 |  | In/out scope, touched surface, contract |  | command/artifact/observation | concrete pass condition |

Then add:

- execution order and why
- parallelizable groups and serialization points
- assumptions and decisions
- risks or modules that may need re-cutting
- first module to start now
- output file paths, if task files were written

For implementation sessions, keep the active module visible. Do not drift into
later modules without saying which boundary changed.
