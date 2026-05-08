# Qwen3-Next PyTorch PR History

Snapshot date: 2026-05-08.

Scope: Qwen3-Next PyTorch model and runtime support.

## Main Files

- `lmdeploy/pytorch/models/qwen3_next.py`
- `lmdeploy/pytorch/configurations/qwen3_next.py`
- `lmdeploy/pytorch/engine/cache_engine.py`
- `lmdeploy/pytorch/engine/model_agent.py`
- `lmdeploy/pytorch/kernels/cuda/pagedattention.py`
- `lmdeploy/pytorch/paging/scheduler.py`
- `lmdeploy/pytorch/paging/state_manager.py`

## PR Timeline

| Date | PR | Commit | PyTorch relevance |
| --- | --- | --- | --- |
| 2025-11-07 | [#4039](https://github.com/InternLM/lmdeploy/pull/4039) | `281e1017` | Added Qwen3-Next PyTorch support, recurrent cache handling, scheduler/cache changes, paged-attention updates, environment checks, and model registration. |

## Optimization Notes

- Treat Qwen3-Next as model support plus runtime support. The first PR touched
  cache engine, state manager, scheduler, model inputs, graph runner, and
  paged-attention code.
- Environment checks matter. Qwen3-Next CUDA support depends on
  Flash Linear Attention availability.
- Long-context and cache lifecycle bugs are more likely than simple loader bugs.

## Validation Lanes

- Import and env-check failure mode without required FLA dependency.
- Basic PyTorch pipeline smoke when dependencies are present.
- Long-context decode.
- Recurrent-state cache allocation and release.
- CUDA graph capture path.
- Paged-attention path.
- Scheduler/state-manager interaction during prefill and decode.
