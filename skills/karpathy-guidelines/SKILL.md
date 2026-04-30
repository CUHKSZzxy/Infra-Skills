---
name: karpathy-guidelines
description: "Use when writing, reviewing, or refactoring code to stay surgical: surface assumptions, avoid speculative features, touch only necessary lines, and define verifiable success criteria."
license: MIT
---

# Karpathy Guidelines

Small guardrails for non-trivial coding work. Bias toward simple, verified
changes over clever or expansive ones.

## Rules

- State assumptions when they affect the implementation.
- Ask or investigate when the task is ambiguous enough to change the design.
- Build the minimum requested behavior; skip speculative flags, aliases,
  abstractions, and compatibility paths.
- Keep public API surface smaller than the experimental branch surface until
  semantics, tests, backend support, and users are clear.
- Touch only files and lines needed for the task. Match local style.
- Do not refactor or clean unrelated code unless explicitly asked.
- Remove only dead code introduced by your own change.
- Define success as concrete checks: targeted tests, smoke tests, lint, or a
  reproducible command.
- If validation cannot run, say exactly what was not run and why.
