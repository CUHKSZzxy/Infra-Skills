---
name: lmdeploy-attention-dataflow
description: Use when tracing LMDeploy attention dispatch, KV layout, or quantization contracts.
---

# LMDeploy Attention And KV Dataflow

Verify the active path in the target checkout: dispatch gates depend on branch,
GPU, CUDA, and installed kernels. Start at
`lmdeploy/pytorch/backends/cuda/attention/__init__.py`, particularly
`TritonAttentionBuilder.build`, `_enable_fa3`, and `use_flash_mla`.
The broad selection is FlashMLA, eligible FA3, then default Triton attention;
current code determines the actual gates.

## Affected Contracts

For a backend change, identify the selected implementation, prefill/decode mode,
quant policy, cache dtype/scale layout, and relevant shape. Trace only reachable
paths and shared metadata contracts; an excluded optional backend does not need
a separate investigation.

For a public policy change, trace parsing/config through allocation, module
state, dispatch, and kernel arguments. Parsing a quantization label does not
establish runtime support. Cache fill and all affected readers must agree on
payload and scale/zero metadata; reject unsupported layouts near dispatch.
Account for prefill flattening, speculative readers, and MLA/non-MLA differences
when reachable.

If the change adds module-owned scales, buffers, or metadata used in serving,
check a small generation after the affected release/reload/wakeup flow. Tensor
ownership must restore device, dtype, and metadata before kernel use.

## Backend References

Use [backend paths](references/backend-paths.md) for the active call chain:
shared KV fill, Triton decode/prefill, FA3/speculative paths, FlashMLA, or GLM-5.2
sparse DSA with BF16/FP8 MLA cache. Locate moved symbols in the checkout rather
than treating this map as the implementation. Use `optimize-kernel` when the
resolved path needs correctness or timing work.
