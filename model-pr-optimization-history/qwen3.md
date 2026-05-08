# Qwen3 PyTorch PR History

Snapshot date: 2026-05-08.

Scope: Qwen3 dense and Qwen3-MoE changes that matter for LMDeploy PyTorch
optimization.

## Main Files

- `lmdeploy/pytorch/models/qwen3.py`
- `lmdeploy/pytorch/models/qwen3_moe.py`
- `lmdeploy/pytorch/models/module_map.py`
- `lmdeploy/pytorch/nn/linear.py`
- `lmdeploy/lite/apis/calibrate.py`
- `lmdeploy/lite/quantization/awq.py`

## PR Timeline

| Date | PR | Commit | PyTorch relevance |
| --- | --- | --- | --- |
| 2025-03-25 | [#3315](https://github.com/InternLM/lmdeploy/pull/3315) | `213faf21` | Added PyTorch Qwen3 and Qwen3-MoE model files plus module map entries. This is the baseline for dense attention, MoE routing, loader behavior, and CUDA graph support. |
| 2025-04-29 | [#3499](https://github.com/InternLM/lmdeploy/pull/3499) | `0e6b2e57` | Fixed replicated KV handling for Qwen3-MoE. Recheck KV head replication when changing GQA/MQA, TP, or cache layout code. |
| 2025-04-29 | [#3503](https://github.com/InternLM/lmdeploy/pull/3503) | `b4854b1a` | Added Qwen3 AWQ calibration and quantization support. Quant changes may need lite calibration checks, not only runtime launch checks. |
| 2025-04-30 | [#3505](https://github.com/InternLM/lmdeploy/pull/3505) | `8e0c15d7` | Added Qwen3 FP8 support through PyTorch model files and linear-layer dispatch. Watch scale loading, dtype conversion, and linear fallback behavior. |
| 2025-06-04 | [#3582](https://github.com/InternLM/lmdeploy/pull/3582) | `46176660` | Added EPLB support for Qwen3-MoE. Validate routed expert distribution and load-balance metadata, not just output correctness. |
| 2026-02-13 | [#4293](https://github.com/InternLM/lmdeploy/pull/4293) | `aa398972` | Added ignore-layer support in Qwen3 quant config. Keep quant config parsing aligned with model loader assumptions. |

## Optimization Notes

- Start from `qwen3_moe.py` for MoE routing and loader changes; many Qwen3
  regressions are shape or metadata mistakes rather than kernel issues.
- FP8 and AWQ touch different layers of the stack. FP8 mostly follows runtime
  model and linear dispatch paths; AWQ also touches lite calibration.
- EPLB work should be validated with expert statistics or routed-expert output.
  A single text-generation smoke test can miss bad balancing metadata.

## Validation Lanes

- Dense BF16/FP16 pipeline smoke.
- MoE BF16/FP16 pipeline smoke.
- Tensor parallel Qwen3-MoE launch.
- Qwen3-MoE replicated KV shape check.
- AWQ calibration or quantized model load.
- FP8 model load with scale sanity.
- EPLB/routed-expert sanity when MoE routing code changes.
