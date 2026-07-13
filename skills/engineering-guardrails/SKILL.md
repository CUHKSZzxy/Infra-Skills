---
name: engineering-guardrails
description: Use when planning, implementing, or reviewing code; apply by default for scope control, local style, simple design, and concrete validation without over-defensive code or dummy tests.
---

# Engineering Guardrails

Apply these guardrails by default to code planning, implementation, and review.
Bias toward simple, verified changes over clever or expansive ones.

## Planning And Decision Guardrails

- **State assumptions.** Call out assumptions when they affect the
  implementation.
- **Resolve ambiguity early.** Ask or investigate when the task is ambiguous
  enough to change the design.
- **Build the minimum requested behavior.** Skip speculative flags, aliases,
  abstractions, and compatibility paths.
- **Keep APIs narrow until proven.** Keep public API surface smaller than the
  experimental branch surface until semantics, tests, backend support, and
  users are clear.

## Coding Style Guardrails

- **Match local style.** Touch only files and lines needed for the task.
- **Prefer stateless.** Favor helpers that pass inputs in and return outputs
  out over methods that mutate hidden instance state, unless the surrounding
  subsystem already owns stateful behavior.
- **Prefer immutable.** Default to immutable or read-only data; mutate only
  when the algorithm, API contract, or performance path clearly needs mutation.
- **Functions stay small.** Keep functions small enough to review in one pass;
  when one grows past roughly 100 LOC, split cohesive detail into named helpers.
- **Files stay small.** Keep files small enough to understand as one cohesive
  module; split large modules along existing ownership boundaries.
- **Core functions read like pseudocode.** Keep orchestration functions short
  and push mechanical detail into well-named helpers so the top-level flow is
  obvious.
- **Avoid mixins.** Avoid adding new mixin-based behavior; prefer explicit
  composition or plain helper functions unless the local subsystem already uses
  mixins as its established extension mechanism.
- **Prefer protected over public.** Default new helpers and methods to
  private/protected naming; expose only methods or fields that real callers use.
- **Prefer keyword arguments.** Call functions with multiple non-obvious
  arguments by keyword, and design new helper APIs so keyword calls read
  naturally.
- **Pass what you need.** Give a helper the specific values it uses rather than
  a large owner object. If passing the whole object is genuinely the right
  contract, treat it as read-only and return results for the caller to assign.
- **Trust local invariants.** When local invariants already guarantee a value or
  type is valid, use the value directly; do not add guard helpers or
  normalization utilities merely to appear safer.
- **Avoid over-defensive code.** Preserve existing defensive checks unless they
  are proven redundant, unreachable, or harmful; do not add new guards without
  a concrete failure mode.
- **Follow container conventions.** For data containers, follow the project's
  existing local convention instead of introducing a second style. Migrate old
  containers only while touching that file for real work, not in broad
  style-only sweeps.
- **Avoid unrelated refactors.** Do not refactor or clean unrelated code unless
  explicitly asked.
- **Remove only owned dead code.** Remove only dead code introduced by your own
  change.

## Test And Validation Guardrails

- **Avoid dummy tests.** Do not add dummy or low-signal unit tests. A test
  should fail on a plausible regression, assert observable behavior, or protect
  a real contract.
- **Define success concretely.** Use targeted tests, smoke tests, lint, or a
  reproducible command.
- **Report validation gaps.** If validation cannot run, say exactly what was
  not run and why.
