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

## 3. Shared Non-MLA Attention Shape

Default Triton and FA3 implementations both have the same outer pattern:

```text
impl.forward(query, key, value, k_cache, v_cache, attn_metadata)
        |
        |-- if key/value exist
        |      -> fill KV cache
        |
        |-- if attn_metadata.is_decoding
        |      -> decode attention over paged cache
        |
        `-- else
               -> prefill attention over current/flattened sequence
```

Primary files:

- `lmdeploy/pytorch/backends/cuda/attention/default.py`
- `lmdeploy/pytorch/backends/cuda/attention/fa3.py`
- `lmdeploy/pytorch/kernels/cuda/fill_kv_cache.py`
- `lmdeploy/pytorch/kernels/cuda/pagedattention.py`
- `lmdeploy/pytorch/kernels/cuda/flatten_kv_cache.py`
- `lmdeploy/pytorch/kernels/cuda/flashattention.py`

## 4. KV Cache Fill Flow

```text
attention.forward()
        |
        -> fill_kv_cache(...)
              |
              |-- normal/unquantized policy
              |      -> store K/V into paged cache
              |
              `-- quantized policy
                     -> quantize or pack K/V as required
                     -> store K/V cache payload
                     -> store any scale/zero metadata needed by readers
```

Trace both payload and metadata. A quantized cache write is only correct if
every reader path either consumes the metadata or is explicitly blocked.

Code anchors:

- `lmdeploy/pytorch/kernels/cuda/fill_kv_cache.py`
- `lmdeploy/pytorch/backends/cuda/attention/default.py`
- `lmdeploy/pytorch/backends/cuda/attention/fa3.py`

## 5. Default Triton Decode Flow

```text
TritonAttentionImpl.forward()
        |
        -> _forward_decoding()
        |
        -> paged attention wrapper
        |
        -> Triton paged-attention kernel
              |
              |-- read query
              |-- read paged K/V cache through block table
              |-- apply quant metadata if this path supports it
              |-- compute QK
              |-- softmax
              `-- compute PV and write output
```

This is the first path to inspect for autoregressive decode correctness and
latency.

Code anchors:

- `lmdeploy/pytorch/backends/cuda/attention/default.py`: `_forward_decoding`
- `lmdeploy/pytorch/kernels/cuda/pagedattention.py`: paged attention wrapper
  and kernels

## 6. Default Triton Prefill Flow

```text
TritonAttentionImpl.forward()
        |
        -> _forward_prefill()
        |
        |-- when cache-backed flattened K/V is needed
        |      -> flatten_kv_cache(...)
        |
        -> flash attention kernel over contiguous/flattened K/V
```

For performance reviews, check whether prefill reads cache through an extra
flatten/dequant/transform step before attention. This can be very different
from the decode path.

Code anchors:

- `lmdeploy/pytorch/backends/cuda/attention/default.py`: `_forward_prefill`
- `lmdeploy/pytorch/kernels/cuda/flatten_kv_cache.py`
- `lmdeploy/pytorch/kernels/cuda/flashattention.py`

## 7. FA3 Flow

```text
FA3Impl.forward()
        |
        -> fill KV cache
        |
        |-- decode, max_q_seqlen == 1
        |      -> standard decode path
        |      -> usually paged attention wrapper
        |
        |-- decode, max_q_seqlen > 1
        |      -> speculative/multi-token decode path
        |      -> FA3 kvcache wrapper
        |
        `-- prefill
               -> flatten/prepare K/V
               -> FA3 varlen attention
```

Do not assume FA3 subpaths support the same quant metadata as the default
paged-attention path. Verify argument plumbing in the concrete call.

Code anchors:

- `lmdeploy/pytorch/backends/cuda/attention/fa3.py`
- `lmdeploy/pytorch/third_party/flash_attn_interface.py`

If a listed file or symbol has moved in the target checkout, use `rg` for the
class/function name and continue from the discovered call site.

## 8. FlashMLA Flow

```text
FlashMLAImpl.forward()
        |
        -> MLA-specific KV cache fill
        |
        |-- decoding
        |      -> FlashMLA decode with kvcache
        |
        `-- prefill
               -> flatten/prepare MLA cache
               |-- sparse/NSA path, when enabled
               |-- FA3 prefill path, when enabled
               `-- Triton prefill fallback
```

MLA cache layout and scale placement can differ from regular MHA/GQA cache
layout. Trace the MLA fill, flatten, and decode helpers together instead of
projecting the default attention path onto MLA.

Code anchors:

- `lmdeploy/pytorch/backends/cuda/attention/mla.py`
- `lmdeploy/pytorch/kernels/cuda/flatten_kv_cache.py`
- FlashMLA third-party wrapper imported by `mla.py`

## 9. Correctness Checklist

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

## 10. Runtime Lifecycle State

When a KV-cache or attention change adds module-owned state such as quant
scales, registered buffers, or optional metadata tensors, include a serving
lifecycle check if that feature is reachable in serve mode.

After resource release, reload, or wakeup flows, run a small generation that
exercises the changed KV path. Confirm the owner of each tensor restores the
expected device, dtype, and metadata contract before it is passed to kernels.
