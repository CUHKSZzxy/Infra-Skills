---
name: pr-workflow
description: Use when creating, updating, reviewing, or pushing an LMDeploy pull request. Verify repo state, branch, remote, `gh` or GitHub API access, validation, staged files, and target branch before commit, push, or PR actions.
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
# Replace <env> with the repo env, commonly fp8 or vl on this machine.
source /nvme1/zhouxinyu/miniconda3/etc/profile.d/conda.sh && conda activate <env>
command -v gh && gh auth status
```

Confirm:

- this is the intended LMDeploy checkout and branch,
- unrelated local changes are understood and left unstaged,
- the base branch and push remote are known,
- the available PR tool is known: `gh`, GitHub API via git credential, or browser URL,
- the right env is available (`fp8` for `lmdeploy_fp8`, `vl` for `lmdeploy_vl`).

Prefer `gh` from the repo's conda env before falling back to raw GitHub API.
On this machine, `gh` is commonly available after activating `fp8` or `vl`.

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
gh pr create --repo InternLM/lmdeploy --base <base> --head <fork>:<branch> --title "<type>: <summary>" --body-file <body.md>
```

If `gh` is unavailable, push first and use the fallback that matches the
machine:

- If `git push` prints a GitHub "new pull request" URL, report that URL.
- If a git credential helper can provide a GitHub token, create the PR through
  the GitHub API without printing the token.
- If neither exists, report the pushed branch, intended base/head, and PR body
  path so the user can open the browser URL.

## 3. Existing PR / Review Fix Path

Confirm the PR branch first:

```bash
gh pr view <PR> --repo InternLM/lmdeploy
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
the PR head branch. For an existing fork PR, prefer an explicit push target:

```bash
git push origin HEAD:<headRefName>
```

If a pushed commit was amended and the remote branch must be rewritten, fetch
the remote tip first and use a pinned lease rather than a broad force push:

```bash
git fetch origin <branch>:refs/remotes/origin/<branch>
git log --oneline --left-right --cherry-pick origin/<branch>...HEAD
git push --force-with-lease=<branch>:<old-remote-sha> origin HEAD:refs/heads/<branch>
```

Use this only when the left/right comparison shows the remote-only commit is the
old version you intentionally replaced. If the remote has unrelated new work,
integrate it instead of rewriting it.

## 4. Merging Base Branch Updates

Before merging `main` or another base branch, commit the feature work first.
After conflicts are resolved, run targeted tests for both the feature files and
the conflicted neighboring surface. If a test failure is caused by sandbox,
network, or environment limits, rerun the same command in the correct env before
changing code.

Keep merge conflict resolutions additive where both sides introduced real
support. Update nearby tests when the resolved behavior intentionally broadens a
supported API surface.

## 5. Validation And Lint

Prefer targeted checks during iteration; broaden before final push.

```bash
pre-commit run --files <changed-files>
pytest <targeted-tests>
```

Use `pre-commit run --all-files` when the checkout is clean enough to interpret.
If CI says a hook modified files, rerun that hook locally and inspect
`git diff --name-only` before committing; hook auto-fixes can touch unrelated
files in large or dirty worktrees.

## 6. Output Contract

Report:

- branch and remote pushed,
- commit SHA,
- validation commands and pass/fail status,
- PR URL or review comments addressed.
