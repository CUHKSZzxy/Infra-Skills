# Local Conventions

Machine-specific paths and env names for this workspace. Treat these as local
defaults, not general project facts.

## Paths

- Home: `/home/zhouxinyu`
- LMDeploy dev checkout: `/home/zhouxinyu/lmdeploy_dev`
- LMDeploy multimodal checkout: `/home/zhouxinyu/lmdeploy_mm`
- vLLM source checkout: `/home/zhouxinyu/vllm_dev`
- SGLang source checkout: `/home/zhouxinyu/sglang_dev`
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
LMDEPLOY_DEV_SOURCE=/home/zhouxinyu/lmdeploy_dev
LMDEPLOY_MM_SOURCE=/home/zhouxinyu/lmdeploy_mm
VLLM_DEV_SOURCE=/home/zhouxinyu/vllm_dev
SGLANG_DEV_SOURCE=/home/zhouxinyu/sglang_dev
CONDA_EXE=/home/zhouxinyu/miniconda3/bin/conda
CONDA_PROFILE=/home/zhouxinyu/miniconda3/etc/profile.d/conda.sh
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

- `dev`: paired with `/home/zhouxinyu/lmdeploy_dev`.
- `mm`: paired with `/home/zhouxinyu/lmdeploy_mm`.

Assume each checkout is installed from source in its paired env.
The vLLM and SGLang checkouts are source references for comparison; no paired
conda env is declared here for them.

If `import lmdeploy` raises dependency errors, report env preparation or
package drift instead of changing the source checkout convention.

Use the direct env interpreter for deterministic commands:

```bash
/home/zhouxinyu/miniconda3/envs/dev/bin/python
/home/zhouxinyu/miniconda3/envs/mm/bin/python
```

If the shell is not initialized for conda yet:

```bash
source /home/zhouxinyu/miniconda3/etc/profile.d/conda.sh
conda activate <paired-env>
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
