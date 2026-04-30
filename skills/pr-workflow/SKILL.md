---
name: pr-workflow
description: Use when creating, updating, reviewing, or pushing an LMDeploy pull request. Verify repo state, branch, remote, `gh` auth, validation, staged files, and target branch before commit, push, or PR actions.
---

# LMDeploy PR Workflow

Use this for both new PRs and existing PR review fixes. Keep the loop small:
understand the branch, change only intended files, validate, then commit/push.

## 1. Preflight

Before fetching comments, changing branches, or pushing:

```bash
git remote -v
git branch --show-current
git status --short
gh auth status
```

Confirm:

- this is the intended LMDeploy checkout and branch,
- unrelated local changes are understood and left unstaged,
- the base branch and push remote are known,
- the right env is available (`fp8` for `lmdeploy_fp8`, `vl` for `lmdeploy_vl`).

## 2. New PR Path

If no feature branch exists:

```bash
git switch <base-branch>
git pull --ff-only
git switch -c <type>/<short-description>
```

Implement the change, then run the narrowest meaningful validation first.
Before committing, inspect the staged diff and stage explicit files only:

```bash
git add <intended-files>
git diff --cached --stat
git commit -m "<type>: <summary>"
git push -u origin <branch>
```

Create the PR only after confirming base/head branches and committed contents:

```bash
gh pr create --repo InternLM/lmdeploy --title "<type>: <summary>" --body-file <body.md>
```

## 3. Existing PR / Review Fix Path

Confirm the PR branch first:

```bash
gh pr view <PR>
```

Fetch inline comments when needed:

```bash
gh api repos/InternLM/lmdeploy/pulls/<PR>/comments
gh api repos/InternLM/lmdeploy/pulls/<PR>/reviews
```

For each actionable comment:

- read surrounding code, not just the flagged line,
- verify the comment still applies,
- make the smallest fix that resolves it,
- keep a short note of file, issue, and fix.

Commit review fixes only after validation and staged-file review, then push to
the PR head branch.

## 4. Validation And Lint

Prefer targeted checks during iteration; broaden before final push.

```bash
pre-commit run --files <changed-files>
pytest <targeted-tests>
```

Use `pre-commit run --all-files` when the checkout is clean enough to interpret.
If CI says a hook modified files, rerun that hook locally and inspect
`git diff --name-only` before committing; hook auto-fixes can touch unrelated
files in large or dirty worktrees.

## 5. Output Contract

Report:

- branch and remote pushed,
- commit SHA,
- validation commands and pass/fail status,
- PR URL or review comments addressed.
