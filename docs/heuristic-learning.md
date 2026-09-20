# Heuristic Learning Framework

Preserve recurring LMDeploy lessons that change future decisions. Keep raw
session history, one-off logs, private payloads, and generic coaching out of
skills. A retrospective can end without a skill update.

## Where Lessons Belong

| Content | Home |
| --- | --- |
| Triggers, essential constraints, and reference links | `skills/*/SKILL.md` |
| Task-specific examples, file maps, and pitfalls | `skills/*/references/` |
| Reusable mechanical checks or benchmark helpers | `skills/*/scripts/` |
| Machine paths, environments, linking, and artifact layout | `docs/conventions/` |
| Raw history and facts that do not warrant a skill | Session notes or memory |

Prefer updating an existing file. Add a skill only for a distinct, recurring
workflow; defer lessons whose reuse is uncertain. Keep machine-specific paths
in [machine conventions](conventions/machines.md).

## Review And Validate

Remove duplicate, stale, or superseded guidance. Check that:

- triggers distinguish workflows without activating too broadly;
- mandatory steps protect concrete contracts;
- references match the target checkout and tools;
- guidance preserves domain knowledge rather than coaching basic capabilities;
- README matches the available skills.

Run the relevant checks in [environment conventions](conventions/environments.md).
After adding or removing skills, follow [linking conventions](conventions/linking.md)
and verify the local symlinks when available.
