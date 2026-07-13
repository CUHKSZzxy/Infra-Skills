---
name: check-env
description: Use when an LMDeploy command fails with wrong Python, wrong `lmdeploy` import path, missing CUDA/GPU visibility, missing repo tools such as `gh`, or sandbox/network fixture errors.
---

# Check the LMDeploy Dev Environment

## 1. Identify the current repo and env target

First determine which local LMDeploy checkout you are in and which ready-made
env should back it.

Use `../../docs/local-conventions.md` as the source of truth for exact local
paths, conda binaries, GitHub CLI location, and remote protocol preference.
Match the current checkout to the repo/env pairing listed there. Treat that
pairing as a local convention, not universal truth, and assume the checkout is
installed from source in its paired env.

## 2. Check Python and repo wiring

Run these first:

```bash
pwd
which python
python -c "import sys, lmdeploy; print(sys.executable); print(lmdeploy.__file__)"
```

Healthy state:

- `python` points to the paired conda env
- `lmdeploy.__file__` points into the current checkout

If `import lmdeploy` points elsewhere, switch to the paired env first, then
retry. If it fails with a missing dependency, report env preparation or package
drift instead of changing the checkout assumption.

## 3. Activate or recover the right env

Set `CONDA_EXE` and `CONDA_PROFILE` from local conventions before using the
commands below.

```bash
conda env list
conda activate <paired-env>
```

If `conda` is not initialized:

```bash
source "$CONDA_PROFILE"
```

Or invoke conda directly:

```bash
"$CONDA_EXE" run -n <paired-env> python -c "import sys; print(sys.executable)"
```

Do env activation before concluding a Python package is missing. `gh` is not a
conda-env tool; if `command -v gh` fails, check the path in local conventions.

## 4. Check CUDA visibility

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.device_count())"
```

If a specific GPU is needed, pick it explicitly:

```bash
export CUDA_VISIBLE_DEVICES=<gpu_id>
```

## 5. Prefer direct env Python when wrappers are unreliable

If `conda run -n <env> python` resolves unexpectedly, use the env's interpreter
directly for tests and scripts.

Use the paired interpreter listed in the `Envs` section of local conventions.

Example:

```bash
CUDA_VISIBLE_DEVICES=X /path/to/paired-env/bin/python -m pytest ...
```

## 6. Common diagnosis patterns

- `import lmdeploy` fails: wrong env is active or `python` is not from the intended conda env
- `lmdeploy.__file__` points outside the repo: wrong env or wrong install is winning
- `which python` shows system Python: env activation failed
- Torch imports but sees zero GPUs: CUDA visibility, driver, or container issue
- `which gh` fails: check the GitHub CLI path in local conventions
- `conda run` uses the wrong Python: switch to the direct env interpreter
- GitHub HTTPS auth or hanging SSH: follow the GitHub section in local
  conventions before debugging git itself
- pytest fails on DNS, HF metadata, or proxy access: rerun the same command with
  network access before treating it as a code failure
- async tests that use executor threads hang only in the sandbox: rerun outside
  sandbox before debugging application logic

## Output Contract

This skill should help produce:

- The intended repo and env pairing
- The exact command to use next
- The first concrete mismatch: wrong Python, wrong install path, or missing GPU visibility
