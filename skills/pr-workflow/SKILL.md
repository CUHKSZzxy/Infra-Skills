---
name: pr-workflow
description: Use when committing, pushing, opening or updating an LMDeploy PR, resolving PR review feedback, or diagnosing branch, remote, `gh`, or non-fast-forward push issues.
---

# LMDeploy PR Workflow

Use this for both new PRs and existing PR review fixes. Keep the loop small:
understand the branch, change only intended files, validate, then commit.

Never run `git push`, `gh pr create`, or any other command that publishes local
commits/branches unless the user explicitly asks for that publish action in the
current request. Validation success, a clean worktree, an existing PR, or prior
general workflow memory is not push permission.

## 1. Preflight

Before fetching comments, changing branches, or any explicitly requested
publish step:

```bash
git remote -v
git branch --show-current
git status --short
command -v gh && gh auth status
# Use dev for /home/zhouxinyu/lmdeploy_dev, or mm for /home/zhouxinyu/lmdeploy_mm.
source /home/zhouxinyu/miniconda3/etc/profile.d/conda.sh && conda activate <paired-env>
```

Confirm:

- this is the intended LMDeploy checkout and branch,
- unrelated local changes are understood and left unstaged,
- the base branch and push remote are known,
- the available PR tool is known: `gh`, GitHub API via git credential, or browser URL,
- the right env is available (`dev` for `/home/zhouxinyu/lmdeploy_dev`, `mm`
  for `/home/zhouxinyu/lmdeploy_mm`).

On this machine, `gh` is installed at `/home/zhouxinyu/.local/bin/gh`, not in
the conda env. Prefer HTTPS GitHub remotes plus `gh auth setup-git`; SSH to
GitHub may hang in this network. Run `gh auth setup-git` when HTTPS pushes
cannot read credentials or the GitHub credential helper is absent.

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
# Only after explicit user permission to publish:
git push -u origin <branch>
```

When the user explicitly asks to publish/open a PR, create it only after
confirming base/head branches and committed contents:

```bash
gh pr create --repo InternLM/lmdeploy --base <base> --head <fork>:<branch> --title "<type>: <summary>" --body-file <body.md>
```

Before creating or updating the PR body, keep reviewer-facing text portable:

- Do not paste machine-local test commands that include absolute paths, conda
  env names, local GPU IDs, proxy/Ray env vars, private checkpoint/media paths,
  or scratch scripts such as `0_*.sh`.
- Summarize local validation by intent and result instead, for example
  "focused pytest coverage for the dtype path", "syntax checks for touched
  modules", or "diff whitespace check".
- Put exact local commands in chat, session logs, or benchmark artifacts when
  they are useful for audit, but keep upstream PR descriptions free of local
  machine details.
- Include exact commands in the PR body only when they are public, portable,
  and likely to work from a normal checkout.
- When the user wants Codex assistance disclosed, append a final
  `## Assistance` section to the PR body. Use the exact Codex/model/reasoning
  label the user provides, for example `Assisted with Codex + GPT-5.5 xHigh`;
  do not invent or normalize the model/reasoning label.

If the user explicitly asked to publish and `gh` is unavailable, use the
fallback that matches the machine:

- If `git push` prints a GitHub "new pull request" URL, report that URL.
- If a git credential helper can provide a GitHub token, create the PR through
  the GitHub API without printing the token.
- If neither exists, report the pushed branch, intended base/head, and PR body
  path so the user can open the browser URL.
- If an SSH remote hangs, switch the remote to HTTPS and use the `gh` credential
  helper before retrying the push.

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
the PR head branch only when the user explicitly asks to publish the fix. For an
existing fork PR, prefer an explicit push target:

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

Prefer targeted checks during iteration; broaden before final publish when the
user has explicitly requested one.

```bash
pre-commit run --files <changed-files>
pytest <targeted-tests>
```

If `pre-commit` is not installed in the paired env, run the narrowest meaningful
available checks first, such as `python -m unittest discover -s tests` for this
skills repo or targeted pytest in LMDeploy. Use `pre-commit run --all-files`
when the checkout is clean enough to interpret and the tool is installed.
If CI says a hook modified files, rerun that hook locally and inspect
`git diff --name-only` before committing; hook auto-fixes can touch unrelated
files in large or dirty worktrees.

## 6. Output Contract

Report:

- branch and remote pushed, if a push was explicitly requested and completed,
- commit SHA,
- validation run and pass/fail status; keep exact local commands out of PR
  bodies unless they are portable,
- PR URL or review comments addressed.
