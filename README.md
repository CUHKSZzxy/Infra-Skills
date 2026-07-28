# Infra-Skills

Personal skills for LMDeploy development.

This repo is also a small heuristic-learning layer for LMDeploy work: recurring
feedback from sessions is compressed into triggerable skills, references,
or scripts. See `docs/heuristic-learning.md` for the
boundaries and update loop.

## Skills

| Skill | Area |
| --- | --- |
| `/check-env` | Local LMDeploy env, Python, CUDA, and tool wiring |
| `/benchmark-accuracy` | Deterministic model/API correctness checks and dataset passes |
| `/benchmark-efficiency` | Profiler-free end-to-end serving efficiency comparisons |
| `/engineering-guardrails` | Default scope, style, and validation guardrails |
| `/lmdeploy-attention-dataflow` | Attention, KV cache, quant policy, and backend dispatch tracing |
| `/lmdeploy-humanize-review` | Corpus-backed LMDeploy human-style PR/code review |
| `/lmdeploy-prod-incident-triage` | Replay-first production serving incident triage |
| `/lmdeploy-runtime-debugging` | Serve/generation stalls, slow endpoints, and runtime symptoms |
| `/pr-workflow` | Workspace commit/push and LMDeploy PR workflow |
| `/profile-serving-timeline` | Short LMDeploy/vLLM trace capture and bottleneck diagnosis |
| `/support-new-model` | New LLM/VLM PyTorch backend support |
| `/optimize-kernel` | Identified CUDA/Triton kernel correctness and optimization |
| `/update-session-skill` | End-of-session or retrospective compression into reusable skill guidance |

## Heuristic learning framework

- `docs/heuristic-learning.md`: repo boundaries, promotion choices, compression
  checks, and validation expectations.
- `docs/local-conventions.md`: local paths, env names, and symlink conventions.

______________________________________________________________________

## Wiring locally

Link the repo skills into local agent skill directories:

```bash
scripts/link_skills.sh
```

By default this links every folder under `skills/` into both `~/.claude/skills`
and `~/.codex/skills`. Built-in Codex skills under `~/.codex/skills/.system`
are left in place. Stale symlinks that point to removed skills in this repo are
pruned.

Useful variants:

```bash
scripts/link_skills.sh claude
scripts/link_skills.sh codex
scripts/link_skills.sh copilot
scripts/link_skills.sh --dry-run
scripts/link_skills.sh --dest my-agent=/path/to/skills
```

Copilot does not have a standard local skills directory in this workspace. If
your Copilot client watches one, set `COPILOT_SKILLS_DIR` or pass a custom
`--dest`.

For Claude repo-level wiring without symlinks, add this shape to
`.claude/settings.json` in the target repo:

```json
{
  "skillsDirectories": ["/path/to/Infra-Skills/skills"]
}
```

See `docs/local-conventions.md` for the canonical local paths and env names.
