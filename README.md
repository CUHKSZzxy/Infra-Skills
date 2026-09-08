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
| `/engineering-guardrails` | Workspace coding preferences and minimal GPU use |
| `/lmdeploy-attention-dataflow` | Attention, KV cache, quant policy, and backend dispatch tracing |
| `/lmdeploy-prod-incident-triage` | Production evidence preservation and replay |
| `/lmdeploy-runtime-debugging` | Local or reproduced serving and worker failures |
| `/pr-workflow` | Workspace commit/push and LMDeploy PR workflow |
| `/profile-serving-timeline` | Short LMDeploy, vLLM, and SGLang trace capture and bottleneck diagnosis |
| `/review-code` | LMDeploy contract review and optional maintainer corpus evidence |
| `/support-new-model` | New LLM/VLM PyTorch backend support |
| `/optimize-kernel` | CUDA/Triton kernel correctness, optimization, and NCU evidence |
| `/update-session-skill` | End-of-session or retrospective compression into reusable skill guidance |

## Heuristic learning framework

- `docs/heuristic-learning.md`: repo boundaries, promotion choices, compression
  checks, and validation expectations.
- `docs/conventions/machines.md`: local paths, env names, tool locations, and
  repo/env pairings.
- `docs/conventions/environments.md`: env activation and validation commands.
- `docs/conventions/linking.md`: symlink-based skill linking.
- `docs/conventions/deployment-context.md`: benchmark deployment-space context
  captured with each run.
- `docs/conventions/benchmark-artifacts.md`: benchmark run folder and artifact
  layout.

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

See `docs/conventions/machines.md` for canonical local paths and env names, and
`docs/conventions/linking.md` for symlink behavior.

## Optional kernel evidence

`optimize-kernel` can use pinned KernelWiki and Nsight Compute workflow
references without copying their content into the local skill:

```bash
git submodule update --init external/KernelWiki external/ncu-report-skill
```

These submodules are support material for `optimize-kernel`; `link_skills.sh`
continues to expose only the skills owned by this repository.
