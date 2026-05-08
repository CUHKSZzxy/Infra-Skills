# Qwen3.5 PyTorch PR History

Snapshot date: 2026-05-08.

Scope: Qwen3.5 dense, MoE, multimodal, FP8, backend-specific PyTorch support,
and MTP/speculative decoding.

## Main Files

- `lmdeploy/pytorch/models/qwen3_5.py`
- `lmdeploy/pytorch/models/qwen3_5_moe.py`
- `lmdeploy/pytorch/models/qwen3_5_mtp.py`
- `lmdeploy/pytorch/configurations/qwen3_5.py`
- `lmdeploy/pytorch/nn/gated_delta.py`
- `lmdeploy/pytorch/backends/cuda/causal_conv1d.py`
- `lmdeploy/pytorch/backends/cuda/gated_delta_rule.py`
- `lmdeploy/pytorch/kernels/cuda/causal_conv1d.py`
- `lmdeploy/pytorch/spec_decode/*`
- `lmdeploy/pytorch/strategies/ar_spec/*`

## PR Timeline

| Date | PR | Commit | PyTorch relevance |
| --- | --- | --- | --- |
| 2026-02-27 | [#4351](https://github.com/InternLM/lmdeploy/pull/4351) | `3bf75ff9` | Added Qwen3.5 PyTorch dense/MoE and multimodal-style support, causal-conv1d, gated-delta layers, config builder, tests, and docs. |
| 2026-03-04 | [#4394](https://github.com/InternLM/lmdeploy/pull/4394) | `e79a8987` | Added router replay and ignore-quant-layer support for Qwen3.5. Validate expert metadata and quant skip behavior. |
| 2026-03-19 | [#4405](https://github.com/InternLM/lmdeploy/pull/4405) | `f1e1a05c` | Added PyTorch compatibility for Volta-era GPUs: fp16 fallback, fused-MoE autotune choices, and gated-delta state dtype plumbing. |
| 2026-03-28 | [#4470](https://github.com/InternLM/lmdeploy/pull/4470) | `d4e83e16` | Fixed Qwen3.5 FP8 support across causal-conv1d, KV cache flatten/fill, and model files. FP8 validation must include recurrent/conv paths. |
| 2026-04-03 | [#4437](https://github.com/InternLM/lmdeploy/pull/4437) | `12c877c7` | Added Qwen3.5 MTP/speculative decoding with MTP model, spec agent, reject sampler, strategy changes, and tests. |
| 2026-04-08 | [#4485](https://github.com/InternLM/lmdeploy/pull/4485) | `687385e1` | Added Ascend support for Qwen3.5 35B-A3B through dlinfer/Ascend backend hooks and config checks. |
| 2026-05-06 | [#4568](https://github.com/InternLM/lmdeploy/pull/4568) | `cb4cc8a1` | Fixed Qwen3.5-MoE MTP with tensor parallelism greater than one. Always include `tp > 1` in MTP validation. |

## Optimization Notes

- Qwen3.5 is not a plain attention-only model path. Causal conv, gated delta,
  recurrent state, FP8, MoE routing, and MTP can interact.
- Volta support is mainly a dtype and kernel-availability problem. Check bf16
  assumptions and fp16 fallback before deeper debugging.
- FP8 changes must include causal-conv1d and KV cache paths. A linear-only FP8
  smoke is too narrow.
- MTP/spec-decode touches model inputs, proposer logic, reject sampling,
  scheduler behavior, and tensor-parallel coordination.

## Validation Lanes

- Dense Qwen3.5 PyTorch pipeline smoke.
- Qwen3.5-MoE PyTorch pipeline smoke.
- Multimodal Qwen3.5 path if the target checkpoint uses vision inputs.
- Causal-conv1d kernel/unit test.
- Gated-delta recurrent-state dtype check.
- FP8 launch including causal-conv1d and KV cache fill/flatten.
- Router replay and ignore-quant-layer behavior.
- MTP/spec decode acceptance sanity.
- Qwen3.5-MoE MTP with `tp > 1`.
- Volta fp16 fallback if working on SM70/SM75 compatibility.
- Ascend/dlinfer path if backend support is touched.
