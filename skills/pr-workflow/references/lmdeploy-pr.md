# LMDeploy PR Conventions

Use for LMDeploy PR publication, review fixes, or remote-history repair.
Conversation authorization is governed by [the entry point](../SKILL.md).

## Branch And Body

Prefer branch names such as `fix/<summary>`, `feat/<summary>`, or
`docs/<summary>`. Commit and PR titles use the unscoped `<type>: <summary>`
format. Review the delta from the target branch's merge base; a two-dot file
diff can include base-side drift.

Keep reviewer-facing validation portable. Summarize intent and result; exact
commands belong in the PR only when useful in a normal checkout. Keep machine
paths, conda names, GPU IDs, private checkpoints/media, and proxy details in
local artifacts. Supply multiline PR bodies with `--body-file` or a structured
tool argument.

Include an `## Assistance` section when requested or after confirmed manual
review. Use the actual tool/model and known reasoning setting; say "reviewed
manually" only when the user confirms it. Preserve an existing note unless the
task calls for updating it.

For review fixes, verify the comment still applies to the current head and
publish to that PR's head branch when authorized. If renaming a remote branch,
verify the new upstream before deleting the old branch; delete only when that
cleanup is requested.

## Amended Remote Commit

Pin the remote tip before an authorized rewrite:

```bash
git fetch origin <branch>:refs/remotes/origin/<branch>
git log --oneline --left-right --cherry-pick origin/<branch>...HEAD
git push --force-with-lease=<branch>:<old-remote-sha> \
  origin HEAD:refs/heads/<branch>
```

The comparison must show that the remote-only commit is the old version being
replaced. Integrate unrelated remote work. For base updates, preserve feature
work and validate the affected conflict resolutions.

## Access Fallback

Use [machine conventions](../../../docs/conventions/machines.md) for GitHub
CLI/transport failures. A Git credential helper can supply credentials to `gh`
without printing them. If publication remains blocked, retain the prepared body
and report the exact branch/base/head and completed local work.
