---
name: pr-workflow
description: Use when committing, publishing LMDeploy PRs, or resolving branch and remote divergence.
---

# Git And LMDeploy PR Conventions

Push or publish only with explicit user permission covering the changes and
destination. That permission remains valid while completing the authorized
action, including retries; a completed push does not authorize publishing later
follow-up changes. A request to edit or update a skill alone does not authorize
committing or pushing it. When publication is intended but permission is missing,
finish the local preparation before asking.

LMDeploy commit subjects and PR titles use **`<type>: <summary>`**, such as
`fix: handle ...`, without a parenthesized scope. Other repositories retain their
own message conventions.

For LMDeploy PR bodies, review fixes, base integration, or a lease-controlled
rewrite, use [the PR reference](references/lmdeploy-pr.md). It includes the
portable-validation and assistance-note conventions. For environment or GitHub
CLI issues, use [machine conventions](../../docs/conventions/machines.md).

Preserve unrelated remote work when resolving divergence. Rewrite only the
remote commit intentionally replaced, using an explicit lease. Report the
commit/PR, relevant validation, and remaining local changes.
