# LMDeploy Attention Backend Paths

Load only the section that matches the selected runtime path. File names and
symbols may move across branches; when they do, search for the class or function
name and continue from the discovered call site.

## Shared Non-MLA Attention Shape

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

## KV Cache Fill Flow

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

## Default Triton Decode Flow

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

## Default Triton Prefill Flow

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

## FA3 Flow

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

## FlashMLA Flow

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
