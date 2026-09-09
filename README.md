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

Choose the destination directories from
[machine conventions](docs/conventions/machines.md). In shared-storage sessions,
the shell home and agent homes can differ. Preview explicit destinations before
linking:

```bash
scripts/link_skills.sh --dry-run \
  --dest codex=/path/to/codex/skills \
  --dest claude=/path/to/claude/skills
```

Replace the example paths with the intended skill homes, then rerun without
`--dry-run`. Use only the destinations you need; machine-specific paths stay
in the conventions document.

Keep the complete checkout: skills share `docs/` and the root `scripts/`
directory, so copying an individual skill directory is not a supported install.
The linker exposes owned skills and a shared `docs` symlink, preserves built-in
skills under `.system/`, and prunes stale links owned by this repository.

When agent homes are already configured, named targets are also available:

```bash
scripts/link_skills.sh claude
scripts/link_skills.sh codex
scripts/link_skills.sh copilot
scripts/link_skills.sh --dest my-agent=/path/to/skills
```

Named targets use `<AGENT>_SKILLS_DIR`, then `<AGENT>_HOME/skills`, then the
shell home's agent directory. With no targets, the script selects Claude and
Codex. See [linking conventions](docs/conventions/linking.md) for details.

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

See [environment conventions](docs/conventions/environments.md) for validation
commands. The documentation checks validate YAML frontmatter, the skill index,
and local Markdown link targets. They also run through the `skill-docs`
pre-commit hook.

## Optional kernel evidence

`optimize-kernel` can use pinned KernelWiki and Nsight Compute workflow
references without copying their content into the local skill:

```bash
git submodule update --init external/KernelWiki external/ncu-report-skill
```

These submodules are support material for `optimize-kernel`; `link_skills.sh`
continues to expose only the skills owned by this repository.
