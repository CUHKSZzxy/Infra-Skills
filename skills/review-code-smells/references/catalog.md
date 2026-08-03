# Code-Smell Review Catalog

This is a review-oriented paraphrase of the
[Refactoring.Guru code-smell catalog](https://refactoring.guru/refactoring/smells).
Use each item as a diagnostic question. The catalog names a symptom, not an
automatic refactoring mandate.

## Bloaters

- **Long Method.** A routine mixes responsibilities or abstraction levels so a
  reviewer cannot explain its flow in one pass and local changes require
  understanding unrelated detail. Length alone is not proof.
- **Large Class.** A class owns unrelated state or behavior and changes for
  multiple independent reasons. Many cohesive operations over one domain are
  not automatically a smell.
- **Primitive Obsession.** Domain concepts are repeatedly represented by loose
  strings, numbers, flags, or dictionaries, with validation and interpretation
  scattered across callers. Do not wrap values merely to add a type name.
- **Long Parameter List.** Callers repeatedly reconstruct context, ordering is
  easy to misuse, or a stable group of values is threaded through layers.
  Parameter count alone is not proof.
- **Data Clumps.** The same group of values repeatedly travels together through
  fields or signatures and has invariants or meaning as one concept.

## Object-Orientation Abusers

- **Switch Statements.** Type or mode dispatch is duplicated across owners, so
  adding one variant requires synchronized branches. A single localized,
  exhaustive dispatch can be the clearest design.
- **Temporary Field.** Object fields are valid only during one phase or mode,
  creating partially initialized state and conditionals in unrelated methods.
- **Refused Bequest.** A subtype ignores, disables, or violates inherited
  behavior, showing that the base contract does not fit it.
- **Alternative Classes with Different Interfaces.** Implementations provide
  equivalent behavior through inconsistent APIs, forcing callers to adapt or
  branch despite a shared concept.

## Change Preventers

- **Divergent Change.** One module must be edited for several unrelated kinds
  of change, indicating mixed ownership or responsibilities.
- **Shotgun Surgery.** One logical behavior change requires small coordinated
  edits across many modules, increasing omission and drift risk.
- **Parallel Inheritance Hierarchies.** Adding a subtype in one hierarchy
  repeatedly requires a matching subtype in another hierarchy.

## Dispensables

- **Comments.** Explanatory narration compensates for code whose intent or
  structure is obscure, or repeats behavior that can drift. Preserve comments
  that explain rationale, constraints, contracts, or non-obvious performance
  choices.
- **Duplicate Code.** The same behavior or rule exists in multiple places and
  a future fix must stay synchronized. Similar-looking code with distinct
  semantics or performance specialization is not enough.
- **Lazy Class.** An abstraction adds navigation, API surface, or lifecycle
  cost without owning policy, state, translation, or a real variation point.
- **Data Class.** A mutable data holder exposes raw state while its domain
  behavior and invariants are scattered through consumers. DTOs, schemas, and
  serialization boundaries are often intentional.
- **Dead Code.** Changed code leaves unreachable or unused branches, symbols,
  parameters, or feature paths with no supported caller.
- **Speculative Generality.** New hooks, layers, flags, parameters, or extension
  points serve hypothetical future needs rather than a current requirement or
  caller.

## Couplers

- **Feature Envy.** A function mostly interprets or manipulates another
  owner's data, suggesting that behavior and data ownership are separated.
- **Inappropriate Intimacy.** Modules depend on each other's internals, hidden
  state, or update order rather than an explicit stable contract.
- **Message Chains.** Callers traverse object graphs to reach data or behavior,
  coupling them to intermediate structure and ownership.
- **Middle Man.** A wrapper mostly delegates without enforcing policy,
  translating contracts, isolating volatility, or providing another concrete
  boundary benefit.

## Other Smells

- **Incomplete Library Class.** A dependency lacks needed behavior, causing
  repeated local workarounds or reimplementations. Prefer a narrow local
  extension or adapter when the library cannot be changed, but account for
  upgrade and maintenance cost.
