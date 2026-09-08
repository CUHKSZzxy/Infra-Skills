---
name: check-env
description: Use when LMDeploy commands fail because of environment, tool-path, or sandbox setup.
---

# LMDeploy Environment Recovery

[Machine conventions](../../docs/conventions/machines.md) identify the paired
checkout/environment and direct interpreter. LMDeploy is installed from source
in that environment; compare the imported `lmdeploy.__file__` with the intended
checkout before changing packages. A dependency error in the correct pairing
is environment drift, not evidence for selecting a different checkout.

Use the paired interpreter directly when conda wrappers resolve unexpectedly;
source `CONDA_PROFILE` when activation is needed. GitHub CLI has a separate
machine-specific path and need not belong to the paired environment.

For DNS/HF/proxy failures or sandbox-only executor hangs, retry the same command
through an available approved execution path. If that path is unavailable,
report the limitation rather than changing application code to accommodate it.
Resume the original task once the environment mismatch is resolved.
