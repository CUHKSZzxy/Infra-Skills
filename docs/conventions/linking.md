# Linking Conventions

Use [machines.md](machines.md) for `INFRA_SKILLS_HOME`, `CODEX_HOME`, and
`CLAUDE_HOME`.

Expose repo skills by symlink, retaining the complete checkout for shared docs
and scripts. Explicit destinations avoid shell-home differences and override
ambient agent-home settings. After selecting paths from machine conventions:

```bash
scripts/link_skills.sh --dry-run \
  --dest codex="$CODEX_HOME/skills" \
  --dest claude="$CLAUDE_HOME/skills"
```

Inspect the preview, then run the same command without `--dry-run`. Named
targets (`codex`, `claude`, `copilot`) use the corresponding `*_SKILLS_DIR`
setting first, then `*_HOME/skills`, then `$HOME/.<agent>/skills`.

Built-in Codex skills under `$CODEX_HOME/skills/.system` stay in place; custom
repo skills are additive.

`scripts/link_skills.sh` also links this repo's `docs/` directory to a peer
`docs/` directory beside each agent `skills/` directory, such as
`$CODEX_HOME/docs`. Keep this in place so skill references like
`../../docs/conventions/machines.md` resolve from symlinked skill homes. Run
the linker again after changing the docs symlink target or adding a new agent
destination. Docs-only edits do not need relinking when the symlink already
points at this repo.
