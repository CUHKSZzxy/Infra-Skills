# Local Conventions

Select the machine section whose checkout root matches the current session.
Treat these paths as local defaults, not project facts, and do not mix paths or
env assumptions between machines.

## `/home/zhouxinyu` Workstation

Use this section for project paths under `/home/zhouxinyu`.

```bash
WORKSPACE_ROOT=/home/zhouxinyu
INFRA_SKILLS_HOME="$WORKSPACE_ROOT/common/Infra-Skills"
SKILL_SOURCE="$INFRA_SKILLS_HOME/skills"
LMDEPLOY_DEV_SOURCE="$WORKSPACE_ROOT/lmdeploy_dev"
LMDEPLOY_MM_SOURCE="$WORKSPACE_ROOT/lmdeploy_mm"
VLLM_DEV_SOURCE="$WORKSPACE_ROOT/vllm_dev"
SGLANG_DEV_SOURCE="$WORKSPACE_ROOT/sglang_dev"
CODEX_HOME="$WORKSPACE_ROOT/.codex"
CLAUDE_HOME="$WORKSPACE_ROOT/.claude"
CONDA_ROOT="$WORKSPACE_ROOT/miniconda3"
CONDA_EXE="$CONDA_ROOT/bin/conda"
CONDA_PROFILE="$CONDA_ROOT/etc/profile.d/conda.sh"
GH_EXE="$WORKSPACE_ROOT/.local/bin/gh"
```

Env pairings:

| Env | Source checkout |
| --- | --- |
| `dev` | `$LMDEPLOY_DEV_SOURCE` |
| `mm` | `$LMDEPLOY_MM_SOURCE` |

Assume each LMDeploy checkout is installed from source in its paired env. The
vLLM and SGLang checkouts are source references only; no paired env is declared
for them.

`gh` lives at `$GH_EXE`; `.zprofile` and `.zshrc` should put its directory on
`PATH`. GitHub SSH may hang on this machine, so prefer HTTPS with the GitHub CLI
credential helper:

```bash
gh auth setup-git
git remote set-url origin https://github.com/<owner>/<repo>.git
```

## Shared Storage Workspace

Use this section for project paths under
`/mnt/shared-storage-user/zhouxinyu1`. `$HOME` may be `/root`; never derive
project, conda, or agent paths from `$HOME`.

```bash
WORKSPACE_ROOT=/mnt/shared-storage-user/zhouxinyu1
INFRA_SKILLS_HOME="$WORKSPACE_ROOT/common/Infra-Skills"
SKILL_SOURCE="$INFRA_SKILLS_HOME/skills"
LMDEPLOY_DEV_SOURCE="$WORKSPACE_ROOT/lmdeploy_dev"
VLLM_DEV_SOURCE="$WORKSPACE_ROOT/vllm_dev"
CODEX_HOME="$WORKSPACE_ROOT/.codex"
CLAUDE_HOME="$WORKSPACE_ROOT/.claude"
CONDA_ROOT="$WORKSPACE_ROOT/miniconda3"
CONDA_EXE="$CONDA_ROOT/bin/conda"
CONDA_PROFILE="$CONDA_ROOT/etc/profile.d/conda.sh"
TMUX_EXE=/usr/bin/tmux
```

Env pairings:

| Env | Source checkout |
| --- | --- |
| `dev` | `$LMDEPLOY_DEV_SOURCE` |
| `vllm-dev` | `$VLLM_DEV_SOURCE` |

No multimodal LMDeploy checkout, `mm` env, or SGLang checkout is declared on
this machine. Set `LMDEPLOY_MM_SOURCE` or `SGLANG_DEV_SOURCE` only after
confirming the path exists.

`gh` is not on `PATH` in the current container; verify before use. `sudo` is
not usable, so prefer workspace-local or conda installs over `apt`.

Shared-storage checkouts may be owned by `nobody:nogroup`. If Git reports
`detected dubious ownership`, use a command-scoped override:

```bash
git -c safe.directory="$INFRA_SKILLS_HOME" <command>
```

## Common Workflows

### Environments

If `import lmdeploy` raises dependency errors, report env preparation or
package drift instead of changing the checkout convention. Activate the paired
env, or use its interpreter directly for deterministic commands:

```bash
source "$CONDA_PROFILE"
conda activate <paired-env>

"$CONDA_ROOT/envs/<paired-env>/bin/python" <args>
```

For Infra-Skills validation:

```bash
PYTHONDONTWRITEBYTECODE=1 "$CONDA_ROOT/envs/dev/bin/python" -m unittest discover -s tests
git diff --check
```

On shared storage, add `-c safe.directory="$INFRA_SKILLS_HOME"` to the Git
command if ownership requires it. Run targeted hooks only when `pre-commit` is
installed in `dev`:

```bash
"$CONDA_ROOT/envs/dev/bin/pre-commit" run --files <changed-files>
```

### Linking

Expose repo skills by symlink, not copy. Pass explicit agent homes so linking
also works when `$HOME` is `/root`:

```bash
env CLAUDE_HOME="$CLAUDE_HOME" CODEX_HOME="$CODEX_HOME" \
  scripts/link_skills.sh
```

Built-in Codex skills under `$CODEX_HOME/skills/.system` stay in place; custom
repo skills are additive. Docs-only changes to existing symlinked skills do not
require relinking.

## Benchmark Artifacts

Keep local end-to-end accuracy and speed outputs inside the measured checkout:

```text
<source-checkout>/benchmark/e2e_<model>_<dataset-or-workload>[_<feature>]/
```

Honor a user-provided destination. Otherwise use lowercase, shell-friendly
labels under `benchmark/`, not ad hoc top-level `bench_*` folders. State the
assumed checkout before a long run when the destination is ambiguous.

Put `summary.md` at the run root. Keep artifacts in small numbered folders such
as `0_accuracy/`, `0_eval_logs/`, `0_bench_logs/`, `0_analysis/`, and
`0_serve_logs/`. Store server and client logs with the run so comparisons remain
auditable. Final reports must include the run folder and exact `summary.md`
path.

Do not assume datasets exist on a fresh machine. Pass paths explicitly with
`DATASET_PATH` or the script-specific `--data-path`.
