# Local Conventions

Machine-specific paths and env names for this workspace. Treat these as local
defaults, not general LMDeploy project facts.

## Paths

- Infra skills repo: `/nvme1/zhouxinyu/Infra-Skills`
- Skill source: `/nvme1/zhouxinyu/Infra-Skills/skills`
- Codex skill home: `/nvme1/zhouxinyu/.codex/skills`
- Claude skill home: `/nvme1/zhouxinyu/.claude/skills`
- Conda root: `/nvme1/zhouxinyu/miniconda3`

For reusable commands, prefer this variable:

```bash
INFRA_SKILLS_HOME=/nvme1/zhouxinyu/Infra-Skills
```

## Benchmark Artifacts

Keep local end-to-end accuracy and speed benchmark outputs inside the source
checkout being measured:

```text
<source-checkout>/benchmark/e2e_<model>_<dataset-or-workload>/
```

Put `summary.md` at the run root. Use small numbered artifact folders beneath
it, such as `0_accuracy/`, `0_eval_logs/`, `0_bench_logs/`, `0_analysis/`, and
`0_serve_logs/`.

## Envs

- `infra-skills`: docs, hooks, and repo maintenance for this repo.
- `fp8`: local LMDeploy FP8 checkout work.
- `vl`: local LMDeploy VLM checkout work.

Use the narrow repo-doc validation command:

```bash
/nvme1/zhouxinyu/miniconda3/envs/infra-skills/bin/pre-commit run --files <changed-files>
```

## Linking

Expose repo skills by symlink, not copy:

```bash
scripts/link_skills.sh
```

Built-in Codex skills under `/nvme1/zhouxinyu/.codex/skills/.system` should stay
in place; custom repo skills are additive.
