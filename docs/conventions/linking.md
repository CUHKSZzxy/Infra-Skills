# Linking Conventions

Use [machines.md](machines.md) for `INFRA_SKILLS_HOME`, `CODEX_HOME`, and
`CLAUDE_HOME`.

Expose repo skills by symlink, not copy. Pass explicit agent homes so linking
also works when `$HOME` is `/root`:

```bash
env CLAUDE_HOME="$CLAUDE_HOME" CODEX_HOME="$CODEX_HOME" \
  scripts/link_skills.sh
```

Built-in Codex skills under `$CODEX_HOME/skills/.system` stay in place; custom
repo skills are additive.

`scripts/link_skills.sh` also links this repo's `docs/` directory to a peer
`docs/` directory beside each agent `skills/` directory, such as
`$CODEX_HOME/docs`. Keep this in place so skill references like
`../../docs/conventions/machines.md` resolve from symlinked skill homes. Run
the linker again after changing the docs symlink target or adding a new agent
destination. Docs-only edits do not need relinking when the symlink already
points at this repo.
