---
name: review-code-smells
description: Use when reviewing a current diff, PR, patch, or local changes for concrete maintainability problems from the Refactoring.Guru code-smell catalog; focus on smells introduced or materially worsened by the change, not generic style preferences.
---

# Review Code Smells

Review changed code for maintainability risks using the catalog in
`references/catalog.md`. Treat a smell as a prompt to investigate, not proof
that a refactor is required.

Use `engineering-guardrails` alongside this skill. For an LMDeploy maintainer
review, also use `lmdeploy-humanize-review`; keep correctness, performance, and
maintainer-policy findings separate from code-smell findings.

## Scope

Default to the user's current changes. Start with:

```bash
git status --short
git diff HEAD
git ls-files --others --exclude-standard
```

`git diff HEAD` covers staged and unstaged tracked changes, but not untracked
files. Read relevant untracked files explicitly. For a PR or branch review,
also compare `HEAD` with the merge base of the target branch. Do not silently
review the whole repository.

Read enough surrounding code, callers, tests, and local conventions to
understand ownership and change cost. Use history only when intent or whether
debt is pre-existing remains unclear.

## Review Workflow

1. Summarize the changed behavior and affected ownership boundaries.
2. Read `references/catalog.md` and shortlist only smells supported by the
   changed code or its immediate integration path.
3. For each candidate, establish the symptom, exact evidence, and a plausible
   future change that becomes harder or more error-prone.
4. Classify it as introduced, materially worsened, or pre-existing. Report the
   first two as findings. Mention pre-existing debt separately only when it
   constrains the requested change.
5. Recommend the smallest refactor that addresses the demonstrated cost. Do
   not expand into unrelated cleanup or speculative architecture.
6. Unless the user explicitly asks for fixes, stop after the review. Do not
   modify files or post comments to a remote PR.

## Finding Gate

Report a smell only when all of these are true:

- A specific file and line or structural relationship demonstrates it.
- The concern is more than a line count, parameter count, naming preference,
  or resemblance to a catalog example.
- You can explain the concrete comprehension, coupling, duplication, or change
  cost.
- The proposed direction preserves behavior and is proportionate to that cost.

Size metrics are search hints, not findings. Similar syntax with different
semantics is not duplicate code. A switch is not automatically a smell when it
is localized, exhaustive dispatch. Comments that preserve rationale,
constraints, or contracts are useful. DTOs, schema objects, adapters,
compatibility wrappers, generated code, and framework-required shapes can be
legitimate.

For CUDA, Triton, and serving hot paths, first check whether inlining,
specialization, primitive values, mutation, or duplication is intentional for
performance. Do not recommend abstraction without considering compilation,
dispatch, memory traffic, and benchmark evidence.

## Output

Put findings first, ordered by severity. Use this shape:

```text
[medium] Shotgun Surgery - path/to/file.py:123
Evidence: ...
Change cost: ...
Smallest correction: ...
```

Name the catalog smell and state whether it was introduced or worsened. Keep
one root cause in one finding even when it spans several files. Separate open
questions and relevant pre-existing debt after findings. If no candidate
passes the finding gate, say that no actionable code-smell findings were found
and note any review boundary or unexamined risk.
