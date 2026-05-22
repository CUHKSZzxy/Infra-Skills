# Local Conventions

Machine-specific paths and env names for this workspace. Treat these as local
defaults, not general LMDeploy project facts.

## Paths

- Home: `/home/zhouxinyu`
- LMDeploy source checkout: `/home/zhouxinyu/lmdeploy_dev`
- Infra skills repo: `/home/zhouxinyu/common/Infra-Skills`
- Skill source: `/home/zhouxinyu/common/Infra-Skills/skills`
- Codex skill home: `/home/zhouxinyu/.codex/skills`
- Claude skill home: `/home/zhouxinyu/.claude/skills`
- Conda root: `/home/zhouxinyu/miniconda3`
- Conda binary: `/home/zhouxinyu/miniconda3/bin/conda`
- Conda profile script: `/home/zhouxinyu/miniconda3/etc/profile.d/conda.sh`
- GitHub CLI: `/home/zhouxinyu/.local/bin/gh`

For reusable commands, prefer these variables:

```bash
INFRA_SKILLS_HOME=/home/zhouxinyu/common/Infra-Skills
LMDEPLOY_SOURCE=/home/zhouxinyu/lmdeploy_dev
CONDA_EXE=/home/zhouxinyu/miniconda3/bin/conda
GH_EXE=/home/zhouxinyu/.local/bin/gh
```

## Benchmark Artifacts

Keep local end-to-end accuracy and speed benchmark outputs inside the source
checkout being measured:

```text
<source-checkout>/benchmark/e2e_<model>_<dataset-or-workload>[_<feature>]/
```

If the user names a desired destination, run directory, or source checkout, put
the benchmark folder there instead of choosing a new top-level location. When
the destination is ambiguous, ask or state the assumed checkout before running a
long benchmark.

Use lowercase, shell-friendly labels. Avoid ad hoc top-level folders such as
`bench_*`; keep both accuracy and speed runs under `benchmark/`.

Put `summary.md` at the run root. Use small numbered artifact folders beneath
it, such as `0_accuracy/`, `0_eval_logs/`, `0_bench_logs/`, `0_analysis/`, and
`0_serve_logs/`. Keep server logs and client/eval logs in the same run folder
so later comparisons can be audited without searching the checkout.
Every benchmark final report should include the exact `summary.md` path and
the run folder path.

Do not assume dataset files exist on a fresh machine. Pass benchmark dataset
paths explicitly with `DATASET_PATH` or the script-specific `--data-path`.

## Envs

- `dev`: default LMDeploy development env. Once env preparation is complete,
  assume `/home/zhouxinyu/lmdeploy_dev` is installed from source in this env.

During migration the env may exist before all project dependencies are
installed. Treat `import lmdeploy` dependency errors as env-preparation
evidence, not as proof that the source checkout convention is wrong.

Use the direct env interpreter for deterministic commands:

```bash
/home/zhouxinyu/miniconda3/envs/dev/bin/python
```

If the shell is not initialized for conda yet:

```bash
source /home/zhouxinyu/miniconda3/etc/profile.d/conda.sh
conda activate dev
```

For Infra-Skills repo validation, use this fallback even when `pre-commit` is
not installed:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/zhouxinyu/miniconda3/envs/dev/bin/python -m unittest discover -s tests
git diff --check
```

Use the narrower hook command only after `pre-commit` is installed in `dev`:

```bash
/home/zhouxinyu/miniconda3/envs/dev/bin/pre-commit run --files <changed-files>
```

## GitHub

`gh` is installed under `/home/zhouxinyu/.local/bin`; `.zprofile` and `.zshrc`
should put that directory on `PATH`.

On this machine, GitHub SSH transport may hang. Prefer HTTPS remotes with the
GitHub CLI credential helper:

```bash
gh auth setup-git
git remote set-url origin https://github.com/<owner>/<repo>.git
```

## Linking

Expose repo skills by symlink, not copy:

```bash
scripts/link_skills.sh
```

Built-in Codex skills under `/home/zhouxinyu/.codex/skills/.system` should stay
in place; custom repo skills are additive.
