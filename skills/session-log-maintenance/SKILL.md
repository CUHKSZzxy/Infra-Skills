---
name: session-log-maintenance
description: Use when a project session may span many conversation turns, risks context loss, or the user asks for a durable Markdown or HTML record of objectives, requests, changes, validation, commits, or handoff state.
---

# Session Log Maintenance

Keep a small project-local record so long agent sessions can survive context
loss without forcing the user to reconstruct history.

## When To Start Or Update

Use this when:

- the user asks for a project/session log, journal, handoff, checkpoint, or
  durable record
- the task spans many turns, repos, commits, experiments, or decisions
- context compaction or a future agent handoff would lose useful state
- the user asks to preserve objectives, requests, changes, validation, commits,
  or next steps in a file

Do not turn every short task into paperwork. If the work is small and already
finished, summarize in chat unless the user asks for a file.

## File Choice

Prefer Markdown. Use HTML only when the user asks for a rendered/status page or
the project already uses HTML notes.

Choose the smallest durable home:

- user-provided path, if given
- project repo: `docs/agent-session-log.md`
- multi-repo/shared effort: `/nvme1/zhouxinyu/common/session-logs/<project>.md`
- HTML mirror, when requested: same basename with `.html`

If a log already exists, update it instead of creating a duplicate.

## What To Record

Keep entries factual and compact:

- objective and current success criteria
- user requests in chronological order
- decisions, assumptions, and why they matter
- files changed or moved, using absolute paths when useful
- validation commands and outcomes
- commits, branches, remotes, PRs, and push status
- unresolved questions, blockers, and next actions

Avoid:

- raw secrets, tokens, private credentials, or giant logs
- speculative narrative that will age poorly
- copying full command output when a one-line result is enough
- hiding uncertainty; mark it as `pending`, `not run`, or `needs user decision`

## Update Rhythm

1. At the start of a long task, create or refresh the header.
2. After each meaningful request or design change, append a short timeline item.
3. After file edits, record only user-relevant paths and intent.
4. After validation, record command plus pass/fail/blocker.
5. After commit/push/PR work, record SHA, branch, remote, and status.
6. Before stopping, add a `Current State` and `Next Actions` section.

Use `templates/session-log.md` when creating a new Markdown log. Trim sections
that do not apply.

## HTML Notes

When HTML is requested, keep Markdown as the source of truth unless the user
explicitly wants HTML-only. The HTML should be static and simple: title, current
state, timeline table, changed files, validation, commits, and next actions.
