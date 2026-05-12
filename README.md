# Infra-Skills

Personal skills for LMDeploy development.

This repo is also a small heuristic-learning layer for LMDeploy work: recurring
feedback from sessions is compressed into triggerable skills, references,
scripts, or model-history notes. See `docs/heuristic-learning.md` for the
boundaries and update loop.

## Skills

| Skill | Area |
| --- | --- |
| `/check-env` | Local LMDeploy env, Python, CUDA, and tool wiring |
| `/karpathy-guidelines` | Surgical coding and review guardrails |
| `/llm-e2e-benchmark` | End-to-end serving benchmark matrices, logs, and summaries |
| `/lmdeploy-attention-dataflow` | Attention, KV cache, quant policy, and backend dispatch tracing |
| `/lmdeploy-runtime-debugging` | Serve/generation stalls, slow endpoints, and runtime symptoms |
| `/pr-workflow` | LMDeploy PR creation, review fixes, validation, and push |
| `/session-skill-maintenance` | End-of-session compression into skills, refs, scripts, or history |
| `/support-new-model` | New LLM/VLM PyTorch backend support |
| `/triton-kernel-performance` | CUDA/Triton correctness, benchmarking, and performance work |

## Model PR optimization history

- `model-pr-optimization-history/qwen3.md`: Qwen3 dense/MoE PyTorch notes.
- `model-pr-optimization-history/qwen3vl.md`: Qwen3-VL PyTorch and VL-serving notes.
- `model-pr-optimization-history/qwen3omni.md`: Qwen3-Omni PyTorch and
  audio/video preprocessing notes.
- `model-pr-optimization-history/qwen3-next.md`: Qwen3-Next PyTorch notes.
- `model-pr-optimization-history/qwen35.md`: Qwen3.5 PyTorch, MoE, and MTP notes.

## Heuristic learning framework

- `docs/heuristic-learning.md`: repo boundaries, promotion choices, compression
  checks, and validation expectations.
- `docs/local-conventions.md`: local paths, env names, and symlink conventions.
- `templates/lesson-candidate.md`: scratchpad for deciding whether a session
  lesson should become a skill, reference, script, model-history note, or
  nothing.

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
