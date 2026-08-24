# LMDeploy Attention Backend Paths

Load only the section that matches the selected runtime path. File names and
symbols may move across branches; when they do, search for the class or function
name and continue from the discovered call site.

## Contents

- [Shared Non-MLA Attention Shape](#shared-non-mla-attention-shape)
- [KV Cache Fill Flow](#kv-cache-fill-flow)
- [Default Triton Decode Flow](#default-triton-decode-flow)
- [Default Triton Prefill Flow](#default-triton-prefill-flow)
- [FA3 Flow](#fa3-flow)
- [DSA Indexer Flow](#dsa-indexer-flow)
- [FlashMLA Flow](#flashmla-flow)
- [GLM-5.2 Sparse DSA: BF16 Versus FP8 MLA KV Cache](#glm-52-sparse-dsa-bf16-versus-fp8-mla-kv-cache)

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

## DSA Indexer Flow

```text
Indexer.forward()
        |
        |-- prepare current Q and its per-head gate/quant scale
        |-- prepare current K and append it to the paged indexer K cache
        |-- score history with sum_h gate_h * relu(Q_h @ K)
        `-- top-k token positions -> nsa_indices -> sparse MLA attention
```

The indexer cache is separate from the main MLA KV cache. The indexer has no V
path because it ranks tokens without aggregating values; V participates only
afterward in sparse MLA attention. Q is current-step state and is not cached,
while historical K must be cached for future queries. Verify callers before
judging helper ownership: a standalone K-preparation wrapper may exist only as
a reference for testing while the runtime fused path writes K directly into
the indexer cache.

Code anchors:

- `lmdeploy/pytorch/models/deepseek_v32.py`: `Indexer.forward`
- `lmdeploy/pytorch/backends/cuda/nsa.py`: `TritonNSAIndexFP8`
- `lmdeploy/pytorch/kernels/cuda/dsa_indexer_preprocess.py`
- `lmdeploy/pytorch/kernels/cuda/ds_index.py`

### DSA Dense-Boundary Shortcut

During decode, when the largest KV sequence in the active batch is no longer
than `index_topk`, top-k must select every causally visible token. A safe
shortcut may therefore emit identity logical indices and skip Q preparation,
score computation, and sorting. It must still:

- project, normalize, rotate, quantize, and append the current K to the indexer
  cache;
- emit one causal row for every query token, including speculative multi-token
  decode rows, with invalid positions padded by the normal sentinel;
- use the batch maximum KV length so a mixed batch containing any longer
  sequence falls back to the sparse path;
- preserve the original path above the boundary and for unsupported backends;
- separate dense and sparse CUDA graph variants, while normalizing the key
  when another path reuses saved indices and the choice is irrelevant.

Validate the shortcut with exact-index tests, forced-old-path output parity, a
batch-size sweep, and a timeline showing that the skipped indexer kernels
actually disappear. A truncated model is suitable for parity and performance
checks, but not for claiming full-model task accuracy.

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

### GLM-5.2 Sparse DSA: BF16 Versus FP8 MLA KV Cache

Treat these as independent choices before tracing this path:

- checkpoint/model weight dtype;
- the separate DSA indexer Q/K representation;
- the main MLA KV-cache dtype selected by `--quant-policy`.

`--quant-policy` controls KV-cache storage, not model weights. The GLM-5.2 DSA
indexer remains a separate low-precision path in both cases: it prepares
quantized Q/K, writes its own packed indexer-K cache, scores with the available
DeepGEMM contiguous/paged MQA path (or the Triton FP8 fallback), and emits
`nsa_indices`. GLM then passes those indices to sparse MLA attention.

#### DSA Indexer Kernel Map

The indexer path is the same for BF16 and FP8 main MLA caches. With indexer
fusion enabled (the default), Triton kernels prepare the current rows and write
the separate packed FP8 indexer cache:

```text
prepare_dsa_indexer_q
  -> Triton: RoPE + FP8 Q quantization + head-gate/score scaling

prepare_dsa_indexer_k_cache
  -> Triton: K LayerNorm + RoPE + FP8 quantization + paged cache write
```

The scoring and selection paths then differ by serving stage:

| Stage | Indexer-K access | Score API | Top-k |
|---|---|---|---|
| Prefill | Triton `flatten_dsa_indexer_k_cache`, once per layer/forward | DeepGEMM `fp8_fp4_mqa_logits` over query-row chunks | TileLang `sparse_index_topk` for K=512/2048; otherwise Triton `bitonic_topk` |
| Decode, including multi-token decode | packed paged cache directly | DeepGEMM `fp8_fp4_paged_mqa_logits` | same top-k dispatch |

Despite the DeepGEMM API name, this GLM path supplies FP8 Q and FP8 K plus K
scales; it is not evidence that the indexer cache is FP4. DeepGEMM emits FP32
scores. When its required MQA APIs or CUDA metadata are unavailable, both
stages fall back to the Triton `fp8_index` kernel.

On the bounded DeepGEMM prefill path, compute the query-row chunk size from
`max_logits_bytes // (max_kv_seqlen * 4)`, reuse the flattened K across chunks,
select top-k immediately, and release each FP32 score chunk. Reserve the same
budget before automatic KV-cache sizing. The default is 512 MiB through
`LMDEPLOY_DSA_INDEXER_MAX_LOGITS_MB`. This bound does not currently cover the
Triton `fp8_index` fallback, so identify the active scorer before claiming the
OOM fix applies.

With no explicit quant policy, current GLM-5.2 configuration selects a BF16
main MLA cache:

```text
prefill:
  Triton fill_kv_cache writes the BF16 MLA cache
    -> Triton flatten_kv_cache gathers paged KV to contiguous BF16
    -> flash_mla_sparse_fwd(query, flattened KV, nsa_indices)

decode:
  Triton fill_kv_cache writes the BF16 MLA cache
    -> expose paged cache through a zero-copy strided BF16 view
    -> translate logical top-k positions to storage offsets
    -> flash_mla_sparse_fwd(query, BF16 cache view, translated indices)
```

With `--quant-policy fp8`, the cache engine first selects the model-specific
`fp8_ds_mla` layout. It may then reset the generic cache quant-policy field to
`NONE`; this is intentional because the specialized MLA writer and reader
dispatch by actual cache dtype/layout. Do not infer BF16 from the later metadata
value without checking `model_config.mla_kv_cache_dtype` and `k_cache.dtype`.

```text
prefill:
  Triton fill_kv_cache_blocked_fp8 writes the latent and scales
    -> Triton fill_kv_cache writes the RoPE component
    -> Triton flatten_kv_cache_mla_fp8 dequantizes to contiguous query dtype (BF16)
    -> flash_mla_sparse_fwd(query, flattened BF16 KV, nsa_indices)

decode:
  same specialized Triton packed-cache writers
    -> flash_mla_with_kvcache(
           paged FP8 cache,
           is_fp8_kvcache=True,
           indices=nsa_indices,
           causal=False)
```

The specialized FP8 MLA record stores the non-positional latent in FP8, its
scales, and the RoPE component in the dtype expected by the writer. Verify the
exact constants and layout in the target checkout rather than assuming a
regular MHA/GQA FP8 cache.

For GLM-5.2, `nsa_indices` selects the sparse prefill branch before the FA3
branch, so neither BF16-cache nor FP8-cache sparse prefill should be labeled
FA3. Typical timeline evidence is:

| Main MLA cache | Prefill attention | Decode attention |
|---|---|---|
| BF16 | Triton flatten, then `flash_mla_sparse_fwd` | zero-copy strided view, then `flash_mla_sparse_fwd` |
| FP8 | Triton FP8 flatten/dequantize, then `flash_mla_sparse_fwd` | paged `flash_mla_with_kvcache(is_fp8_kvcache=True, indices=...)` |

Use this ownership summary when reading traces:

```text
DeepGEMM -> calculate DSA token-selection scores
TileLang -> normal GLM top-k selection (K=2048)
FlashMLA -> perform the selected sparse MLA attention
Triton   -> prepare/fill/flatten caches and provide score/top-k fallbacks
```

Code anchors:

- `lmdeploy/pytorch/configurations/glm_moe_dsa.py`: GLM default MLA cache dtype
- `lmdeploy/pytorch/engine/cache_engine.py`: sparse-MLA quant-policy conversion and allocation
- `lmdeploy/pytorch/models/glm_moe_dsa.py`: DSA indices passed into attention
- `lmdeploy/pytorch/backends/cuda/nsa.py`: indexer preparation, scoring, and top-k
- `lmdeploy/pytorch/backends/cuda/attention/mla.py`: shared cache fill, flatten, and paged decode primitives
- `lmdeploy/pytorch/backends/cuda/attention/sparse_mla.py`: sparse prefill/decode dispatch on refactored branches
- `lmdeploy/pytorch/kernels/cuda/dsa_indexer_preprocess.py`: Triton fused indexer preparation and flattening
