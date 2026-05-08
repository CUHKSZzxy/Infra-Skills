---
name: check-env
description: Use when LMDeploy commands fail because the Python env, CUDA visibility, or tool invocation is wrong. Assume the `fp8` and `vl` conda envs already exist; diagnose the active repo, Python, and GPU first, then use the local env defaults if they match the current checkout.
---

# Check the LMDeploy Dev Environment

## 1. Identify the current repo and env target

First determine which LMDeploy checkout you are in and which ready-made env should back it.

Local defaults:

- `lmdeploy_fp8` -> `fp8`
- `lmdeploy_vl` -> `vl`

Treat these as local conventions, not universal truth.

## 2. Check Python and repo wiring

Run these first:

```bash
pwd
which python
python -c "import sys, lmdeploy; print(sys.executable); print(lmdeploy.__file__)"
```

Healthy state:

- `python` points to the intended conda env
- `lmdeploy.__file__` points into the current repo checkout

If `import lmdeploy` fails or points elsewhere, switch to the correct env first, then retry.

## 3. Activate or recover the right env

```bash
conda env list
conda activate <env-name>
```

If `conda` is not initialized:

```bash
source ~/miniconda3/etc/profile.d/conda.sh
```

On this machine the concrete path is often:

```bash
source /nvme1/zhouxinyu/miniconda3/etc/profile.d/conda.sh
```

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

On this machine, `conda run -n <env> python` may resolve to the wrong Python. If that happens, use the env's interpreter directly for tests and scripts.

Local defaults:

- `/nvme1/zhouxinyu/miniconda3/envs/fp8/bin/python`
- `/nvme1/zhouxinyu/miniconda3/envs/vl/bin/python`

Example:

```bash
CUDA_VISIBLE_DEVICES=X /nvme1/zhouxinyu/miniconda3/envs/<env>/bin/python -m pytest ...
```

## 6. Common diagnosis patterns

- `import lmdeploy` fails: wrong env is active or `python` is not from the intended conda env
- `lmdeploy.__file__` points outside the repo: wrong env or wrong install is winning
- `which python` shows system Python: env activation failed
- Torch imports but sees zero GPUs: CUDA visibility, driver, or container issue
- `conda run` uses the wrong Python: switch to the direct env interpreter
- pytest fails on DNS, HF metadata, or proxy access: rerun the same command with
  network access before treating it as a code failure
- async tests that use executor threads hang only in the sandbox: rerun outside
  sandbox before debugging application logic

## Output Contract

This skill should help produce:

- The intended repo and env pairing
- The exact command to use next
- The first concrete mismatch: wrong Python, wrong install path, or missing GPU visibility
