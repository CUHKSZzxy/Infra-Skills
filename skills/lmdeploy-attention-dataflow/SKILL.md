---
name: lmdeploy-attention-dataflow
description: Use when tracing LMDeploy PyTorch attention, KV-cache, quant-policy, prefill, decode, FA3, or FlashMLA dataflow before reviewing correctness or performance changes.
---

# LMDeploy Attention And KV Dataflow

Use this skill before changing attention, KV cache, quantization, or kernel
dispatch. Start from the runtime path in the target checkout, then verify the
exact backend gates in code because availability flags can change by branch,
GPU, CUDA, and installed third-party kernels.

Pair with `triton-kernel-performance` when the goal is kernel speed or
correctness validation.

Do not scan every optional backend by default. If the task excludes FA3,
FlashMLA, speculative decode, or another path, record that scope and follow only
the active path plus the shared metadata contracts it depends on.

## 1. Locate The Runtime Dispatch

Start at the CUDA attention builder:

- `lmdeploy/pytorch/backends/cuda/attention/__init__.py`
- Key symbols: `TritonAttentionBuilder`, `_enable_fa3`, `build`

High-level selection:

```text
TritonAttentionBuilder.build()
        |
        |-- use_flash_mla is True
        |      -> FlashMLAImpl
        |
        |-- FA3 is available and allowed for this shape/model
        |      -> FA3Impl
        |
        `-- otherwise
               -> TritonAttentionImpl
```

Before judging a path, record:

- selected impl class,
- `is_decoding` vs prefill,
- `use_flash_mla`,
- FA3 availability and shape gates,
- `quant_policy`,
- cache dtype and scale metadata layout,
- `max_q_seqlen`, block size, heads, kv heads, and head dim.

## 2. Trace Public Policy End-To-End

For config, quantization, or backend policy changes, map the whole lifecycle
before editing kernels:

```text
CLI/helper alias
        -> message/config dataclass
        -> cache config and cache descriptors
        -> model agent / cache engine allocation
        -> attention module state
        -> backend dispatch
        -> kernel arguments
        -> tests and docs
```

Do not treat a policy as supported just because it parses. Confirm its cache
payload, optional metadata, and reader paths line up for the selected backend.
If a mode is experimental or backend-specific, keep it private or guard it until
the runtime path, tests, and performance story are all clear.

## 3. Load Backend Path Details As Needed

For concrete call graphs, read `references/backend-paths.md`. Load only the
section needed by the active path:

- shared non-MLA shape and KV fill
- default Triton decode or prefill
- FA3 decode, speculative decode, or prefill
- FlashMLA / MLA cache paths

If a listed file or symbol has moved in the target checkout, use `rg` for the
class/function name and continue from the discovered call site.

## 4. Correctness Checklist

When a backend or quant policy changes, answer these before editing kernels:

- Which impl class is selected for the workload?
- Does cache fill store the payload layout that the reader expects?
- Does every reader receive required quant scale/zero metadata?
- Are unsupported metadata layouts rejected near dispatch?
- Is prefill using the same representation as decode, or does it flatten first?
- Is speculative decode using the same reader path as one-token decode?
- Are MLA and non-MLA paths being treated separately?

If any answer is uncertain, inspect that exact call chain first; do not tune
the kernel yet.

## 5. Runtime Lifecycle State

When a KV-cache or attention change adds module-owned state such as quant
scales, registered buffers, or optional metadata tensors, include a serving
lifecycle check if that feature is reachable in serve mode.

After resource release, reload, or wakeup flows, run a small generation that
exercises the changed KV path. Confirm the owner of each tensor restores the
expected device, dtype, and metadata contract before it is passed to kernels.
