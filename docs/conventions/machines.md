# Machine Conventions

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
SGLANG_DEV_SOURCE="$WORKSPACE_ROOT/sglang_dev"
CODEX_HOME="$WORKSPACE_ROOT/.codex"
CLAUDE_HOME="$WORKSPACE_ROOT/.claude"
CONDA_ROOT="$WORKSPACE_ROOT/miniconda3"
CONDA_EXE="$CONDA_ROOT/bin/conda"
CONDA_PROFILE="$CONDA_ROOT/etc/profile.d/conda.sh"
GH_EXE="$CONDA_ROOT/bin/gh"
TMUX_EXE=/usr/bin/tmux
```

Env pairings:

| Env | Source checkout |
| --- | --- |
| `dev` | `$LMDEPLOY_DEV_SOURCE` |
| `vllm-dev` | `$VLLM_DEV_SOURCE` |
| `sglang-dev` | `$SGLANG_DEV_SOURCE` |

No multimodal LMDeploy checkout or `mm` env is declared on this machine. Set
`LMDEPLOY_MM_SOURCE` only after confirming the path exists.

`gh` lives at `$GH_EXE` and is on `PATH` in the current container. `sudo` is
not usable, so prefer workspace-local or conda installs over `apt`.

Shared-storage checkouts may be owned by `nobody:nogroup`. If Git reports
`detected dubious ownership`, use a command-scoped override:

```bash
git -c safe.directory="$INFRA_SKILLS_HOME" <command>
```
