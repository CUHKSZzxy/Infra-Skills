---
name: pr-workflow
description: Use when committing, publishing LMDeploy PRs, or resolving branch and remote divergence.
---

# Git And LMDeploy PR Conventions

Conversation authorization covers the same action and destination across turns.
A commit request alone does not authorize publishing. When an intended publish
action lacks authorization, finish the local preparation before asking about it.

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
