---
name: pr-workflow
description: Use when committing or pushing changes in a workspace repo, opening or updating an LMDeploy PR, resolving PR review feedback, or diagnosing branch, remote, `gh`, or non-fast-forward push issues.
---

# Git And LMDeploy PR Workflow

Keep the loop small: understand the branch and worktree, validate the intended
change, inspect the staged diff, commit, and publish only when explicitly asked.

Never run `git push`, create a PR, or otherwise publish local work unless the
user asks for that publish action in the current request. Prior permission or a
successful commit is not publish permission.

## 1. Preflight

```bash
git branch --show-current
git status --short
git remote -v
```

Confirm:

- this is the intended repo and branch,
- existing local changes are understood,
- unrelated changes will remain unstaged,
- the target validation environment and remote are known.

Use `../../docs/local-conventions.md` for local envs, GitHub CLI location, and
transport preferences. Check `gh auth status` only when GitHub API or PR work
needs it.

## 2. Review And Validate

Inspect the actual change before staging:

```bash
git diff --check
git diff --stat
git diff
```

Read each intended untracked file explicitly; `git diff` does not show its
contents until it is staged.

Run the narrowest meaningful tests first, then broader checks when the blast
radius warrants them. Prefer the repo's configured hooks:

```bash
pre-commit run --files <changed-files>
pytest <targeted-tests>
```

If a tool is unavailable or blocked by environment/network setup, run the
available equivalent checks and report the exact gap. Do not change code merely
to make an environment-caused failure disappear.

## 3. Stage And Commit

Stage explicit paths, including intended deletions. Do not stage generated
artifacts or unrelated user changes.

```bash
git add <intended-files>
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "<type>: <summary>"
```

Follow the repository's existing message style. Where conventional commits are
used, keep the summary concise, lowercase, and imperative. After committing,
verify the commit and worktree:

```bash
git show --stat --oneline --summary HEAD
git status --short --branch
```

## 4. Publish Only When Asked

Before pushing, confirm the intended remote and destination branch. Prefer an
explicit target when updating an existing remote branch:

```bash
git push origin HEAD:<branch>
```

Afterward, verify tracking or compare the remote tip with `HEAD`. If a push is
rejected, fetch and inspect both sides before integrating or rewriting history.
Do not use force push without proving the remote-only commit is the version
being intentionally replaced.

## 5. LMDeploy PR Work

For an LMDeploy PR, review fixes, PR-body updates, branch naming, GitHub auth
fallbacks, base-branch integration, or a lease-controlled rewrite, read
`references/lmdeploy-pr.md`. Do not load that reference for an ordinary local
commit or push.

## Output Contract

Report:

- commit SHA and validation status,
- branch and remote pushed, only when publishing was requested,
- remaining worktree changes or validation gaps,
- PR URL or review comments addressed, when applicable.
