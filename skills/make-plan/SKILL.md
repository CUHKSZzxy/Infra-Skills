---
name: make-plan
description: Use when the user asks Codex to make, write, review, or save an implementation plan before coding; especially for multi-step code changes, unclear requirements, risky refactors, benchmark plans, or work that needs explicit verification checkpoints.
---

# Make Plan

Create a plan that another agent or engineer can execute without replaying the
whole discussion.

This skill is for creating the plan. Use `project-decomposition` later when the
user wants an existing plan split into parallel task packets for separate Codex
sessions.

## 1. Decide The Plan Size

Scale the plan to the task:

- tiny or already-obvious change: 3-5 bullets in chat, then proceed if the user
  wants implementation
- normal multi-step task: structured plan with tasks and verification
- large or cross-cutting project: plan only the first coherent milestone, or
  recommend `project-decomposition` after a high-level plan exists

Do not turn planning into paperwork. If missing information would change the
approach, ask a focused question; otherwise state assumptions and continue.

## 2. Inspect Context First

Before writing the plan, gather enough evidence to avoid generic steps:

- current repo, branch, and dirty files
- relevant docs, configs, tests, scripts, and recent commits
- existing code boundaries and ownership
- local env or hardware constraints from `../../docs/local-conventions.md`
- user-provided success criteria and non-goals

For LMDeploy development plans, inspect comparable vLLM and SGLang behavior
before designing when the topic has a likely equivalent there. Prefer local
repos at `/home/zhouxinyu/vllm_dev` and `/home/zhouxinyu/sglang_dev`; if they
are unavailable, use upstream sources when network access is allowed. Summarize
what was checked, what design signal it gives, and why any repo was skipped.

Prefer exact paths and commands over abstract advice. If a path or command is
unknown, mark how to discover it instead of inventing it.

## 3. Shape The Approach

For ambiguous work, briefly compare 2-3 approaches and pick one. Keep this
short: explain the tradeoff that changes implementation or validation.

Lock down:

- objective and non-goals
- assumptions that must be verified early
- file or module boundaries
- public API, data, model, benchmark, or runtime contracts affected
- what should not be touched

Use `karpathy-guidelines` for risky implementation plans where scope creep,
over-defensive code, speculative abstractions, or dummy tests are likely.

## 4. Write Verifiable Tasks

Each task should be independently checkable and small enough for focused work.

For each task include:

- purpose
- likely files or contracts touched
- implementation notes, only where non-obvious
- exact verification command or artifact to inspect
- expected pass condition
- failure signal that should stop or reshape the plan

Avoid vague items such as "handle edge cases", "add tests", "clean up", or
"verify everything". Say which edge case, which test surface, which cleanup,
and which check proves it.

Use code snippets only when the exact interface or shape matters. When an
important dataflow, control flow, or API contract is hard to express precisely
in prose, include short pseudocode that fixes the intended shape. Do not paste
large speculative code into plans.

## 5. Save The Plan When Useful

If the user asks for a saved plan, or the plan is likely to be handed to another
session, write Markdown in the target repo, preferring:

```text
docs/plans/YYYY-MM-DD-<topic>.md
```

Use a user-provided path when given. Do not commit the plan unless the user
explicitly asks for commit or publish.

## 6. Plan Format

Use this compact shape:

```markdown
# <Task> Plan

## Goal

## Assumptions And Non-Goals

## Approach

## Tasks

### T1. <Name>
- Purpose:
- Files/contracts:
- Notes:
- Verification:
- Done when:
- Stop if:

## Risks

## First Step
```

For chat-only plans, compress the same content into a short table:

| Task | Boundary | Verification | Done When |
| --- | --- | --- | --- |

## 7. Self-Review Before Hand-Off

Before presenting or saving the plan, check:

- Does every user requirement map to a task or an explicit non-goal?
- Are there TODO/TBD placeholders or vague "test/cleanup later" items?
- Are file paths, commands, and expected results concrete enough?
- Could tasks be executed independently, or should dependencies be explicit?
- Is the first step obvious and low-risk?

Report any remaining uncertainty plainly. If implementation should start next,
state whether to execute inline, save the plan first, or decompose it for
parallel sessions.
