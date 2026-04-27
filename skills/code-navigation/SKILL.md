---
name: code-navigation
description: Use when you need to quickly find the right LMDeploy files for a task or bug. Route by task first, then inspect the likely entry points in `pytorch/`, `vl/`, `serve/`, and top-level orchestration files before editing anything.
---

# Navigate the LMDeploy Codebase

## 1. Start from the task

Do not read the repo top-to-bottom. First classify the task, then inspect the likely entry points.

- New PyTorch model support or model patching: `lmdeploy/pytorch/models/`, `lmdeploy/pytorch/configurations/`, `lmdeploy/archs.py`
- Vision-language preprocessing or modality expansion: `lmdeploy/vl/model/`, `lmdeploy/vl/engine.py`, `lmdeploy/vl/constants.py`
- Serving or OpenAI-compatible API behavior: `lmdeploy/serve/`, especially `core/async_engine.py` and `processors/multimodal.py`
- Pipeline, chat flow, or tokenizer behavior: `lmdeploy/pipeline.py`, `lmdeploy/model.py`, `lmdeploy/tokenizer.py`, `lmdeploy/api.py`
- Runtime scheduling, cache, or execution behavior: `lmdeploy/pytorch/engine/`, `paging/`, `strategies/`, `devices/`
- Kernel, quantization, or backend dispatch issues: `lmdeploy/pytorch/backends/`, `kernels/`, `lite/`

## 2. Use fast search before reading files

Prefer `rg` to find the symbol, architecture name, error string, or config field mentioned in the task.

```bash
rg -n "Qwen3|MyModelForCausalLM|apply_chat_template|CUDA_VISIBLE_DEVICES" lmdeploy
rg --files lmdeploy/vl/model lmdeploy/pytorch/models
```

If the user names a model family, search that name first and inspect the closest existing implementation.

## 3. Common entry points by task

### New model support

- `lmdeploy/pytorch/models/module_map.py`: architecture-to-implementation mapping
- `lmdeploy/pytorch/models/<model>.py`: PyTorch patched model
- `lmdeploy/pytorch/configurations/<model>.py`: custom config builder when default config parsing is not enough
- `lmdeploy/archs.py`: architecture registry and VL routing

### VLM preprocessing

- `lmdeploy/vl/model/base.py`: base classes and multimodal token handling
- `lmdeploy/vl/model/<model>.py`: model-specific VL preprocessing
- `lmdeploy/vl/model/builder.py`: explicit model imports and registry loading
- `lmdeploy/serve/processors/multimodal.py`: serving-time preprocess dispatch

### Chat template or pipeline bugs

- `lmdeploy/model.py`: conversation and chat template logic
- `lmdeploy/pipeline.py`: high-level orchestration
- `lmdeploy/tokenizer.py`: tokenizer wrappers
- `lmdeploy/api.py`: high-level user-facing entry points

### Engine and runtime bugs

- `lmdeploy/pytorch/engine/`: request execution loop and scheduler behavior
- `lmdeploy/pytorch/paging/`: KV cache block management
- `lmdeploy/pytorch/weight_loader/`: checkpoint loading
- `lmdeploy/pytorch/nn/` and `multimodal/`: reusable modules and multimodal input structures

## 4. Follow the dependency chain outward

When you find the first relevant file:

1. Identify the public entry point used by the failing path.
2. Trace one level inward to the implementation it dispatches to.
3. Trace one level outward to the caller or registry that wires it in.

This usually finds the real edit point faster than reading whole directories.

## 5. Practical heuristics

- For architecture-name issues, inspect `architectures` in the model `config.json`, then search that string in `module_map.py` and `archs.py`.
- For VLM token expansion bugs, inspect `vl/model/base.py` and the model-specific file together.
- For serving-only failures, compare `serve/` behavior with direct `pipeline()` behavior to see whether the bug is preprocess, routing, or engine-side.
- For loader errors mentioning missing or unexpected weights, inspect the model file and `weight_loader/` path together.

## Output Contract

This skill should help produce:

- The smallest set of files worth reading first
- The likely owner modules for the task
- The next search terms or symbols to inspect
