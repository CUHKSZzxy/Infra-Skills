# LMDeploy PR And Review Workflow

Load this reference only for LMDeploy PR creation, updates, review fixes,
base-branch integration, or remote-history repair.

## Contents

- New PR branch and merge-base diff
- Portable PR body and assistance note
- PR creation and review fixes
- Lease-controlled amended-commit push
- Base updates and GitHub access fallbacks

## New PR Branch

Start from the intended base only after preserving existing work:

```bash
git switch <base-branch>
git pull --ff-only
git switch -c <type>/<short-description>
```

Prefer typed branch names such as `fix/`, `feat/`, `refactor/`, `docs/`,
`test/`, or `chore/`. Use the repository's conventional commit style for the
title and commits.

If a pushed branch is renamed, push the new branch and verify its upstream
before deleting an old remote branch. Delete the old branch only when the user
asks for that cleanup.

## Inspect The PR Delta

Use the merge-base diff for reviewer-facing scope:

```bash
git log --oneline <base>..HEAD
git diff --stat <base>...HEAD
git diff --name-only <base>...HEAD
```

Do not use a two-dot diff to estimate PR file scope; base-side drift can make it
include changes not introduced by the feature branch.

## PR Body

Keep reviewer-facing validation portable:

- Do not include absolute local paths, conda env names, GPU IDs, private
  checkpoint/media paths, proxy variables, or scratch scripts.
- Summarize local validation by intent and result.
- Include exact commands only when they are public, portable, and useful to a
  normal checkout.
- Keep detailed local commands in chat, session logs, or benchmark artifacts.

When opening a PR for this user after manual review, or when explicitly asked
for the reviewed note, append this exact final section:

```md
## Assistance

Assisted with Codex + GPT-5.5 xHigh Fast, reviewed manually
```

When updating an existing body, preserve its content and replace any trailing
`## Assistance` section with the exact section above.

## Create The PR

Confirm base, head, commits, and body before publishing:

```bash
gh pr create \
  --repo InternLM/lmdeploy \
  --base <base> \
  --head <fork>:<branch> \
  --title "<type>: <summary>" \
  --body-file <body.md>
```

Creating or updating a PR requires explicit publish permission in the current
request.

## Existing PR And Review Fixes

Confirm the PR and head branch first:

```bash
gh pr view <PR> --repo InternLM/lmdeploy
gh api repos/InternLM/lmdeploy/pulls/<PR>/comments
gh api repos/InternLM/lmdeploy/pulls/<PR>/reviews
```

For each actionable comment:

- read the surrounding code and current diff,
- verify the comment still applies,
- make the smallest fix that resolves it,
- run targeted validation and inspect the staged diff.

Push to the confirmed PR head only when asked:

```bash
git push origin HEAD:<headRefName>
```

## Amended Remote Commit

Before rewriting an amended commit, fetch and pin the remote tip:

```bash
git fetch origin <branch>:refs/remotes/origin/<branch>
git log --oneline --left-right --cherry-pick origin/<branch>...HEAD
git push --force-with-lease=<branch>:<old-remote-sha> \
  origin HEAD:refs/heads/<branch>
```

Use this only when the comparison proves the remote-only commit is the old
version intentionally replaced. Integrate unrelated remote work instead of
rewriting it.

## Base-Branch Updates

Commit feature work before merging or rebasing the base branch. After conflict
resolution, validate both the feature surface and neighboring conflicted code.
Preserve real support introduced by both sides rather than resolving conflicts
by dropping one side.

## GitHub Access Fallbacks

If `gh` is unavailable or unauthenticated:

- use the GitHub PR URL printed by `git push` when available,
- use a credential-helper token with `gh` or the GitHub API without printing it,
- otherwise report the pushed branch, intended base/head, and prepared PR body,
- follow local conventions if SSH hangs before retrying transport.
