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
repo skills are additive. Docs-only changes to existing symlinked skills do not
require relinking.
