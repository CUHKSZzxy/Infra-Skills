# LMDeploy Kernel Optimization Patterns

Load this reference when optimizing LMDeploy attention, KV cache, quantization,
or similar CUDA/Triton pipelines. It captures reusable workflow lessons; verify
the exact code in the target checkout before applying any heuristic.

## Stage The Pipeline

Measure these as separate lanes before touching kernels:

- cache fill/write
- paged decode attention
- cache flatten/readback
- prefill attention after flatten/readback
- direct prefill attention when current K/V are available
- end-to-end smoke or throughput

If one lane improves and another regresses, the end-to-end result depends on the
workload mix. Do not claim a pipeline win from a single kernel number.

## LMDeploy Attention/KV Code Anchors

- Backend dispatch: `lmdeploy/pytorch/backends/cuda/attention/__init__.py`
- Default Triton attention flow: `lmdeploy/pytorch/backends/cuda/attention/default.py`
- Cache write and quantized cache write: `lmdeploy/pytorch/kernels/cuda/fill_kv_cache.py`
- Paged decode attention: `lmdeploy/pytorch/kernels/cuda/pagedattention.py`
- Flatten/readback path: `lmdeploy/pytorch/kernels/cuda/flatten_kv_cache.py`
- Prefill attention: `lmdeploy/pytorch/kernels/cuda/flashattention.py`
- Cache allocation and scale metadata: `lmdeploy/pytorch/engine/cache_engine.py`

Pair this with `lmdeploy-attention-dataflow` when FA3, FlashMLA, speculative
decode, or backend dispatch might change the active path.

## Quantized KV Cache Checks

For quantized KV cache, treat payload and metadata as one contract:

- cache fill must write K/V payload and every required scale/zero payload,
- decode must consume metadata in the attention kernel or reject the path,
- flatten/readback must preserve the same dequant direction,
- prefill may be different from decode and may materialize dequantized K/V,
- speculative or multi-token decode may use a separate backend path.

A backend that first dequantizes the whole cache and then calls normal attention
can lose the memory benefit. Prefer fused scale application inside attention, or
bypass cache readback when fresh current K/V are already available.

## Split-K And Occupancy Heuristics

Split-K is a parallelism knob, not a universal speed knob.

Use it when profiling shows the first paged-attention kernel dominates and the
GPU is underoccupied for the target context length. Sweep a small set such as
`1, 4, 8, 16, 32, 64`, but record the forced value in JSONL metadata.

Decision rules:

- If split 1 is slow and mid-range splits improve, the kernel needed more CTAs.
- If very high split regresses, reduce overhead or extra scratch traffic is now too large.
- If short context is flat but long context improves, guard the change by shape or keep the multiplier conservative.
- If the reduce kernel becomes a meaningful fraction of total time, stop increasing split-K.
- If data only covers one GPU generation, guard by capability or rerun on the other generation.

Production heuristic patches should be narrow: one quant policy, one hardware
class, or one shape family at a time.

## Artifact Hygiene

Make artifacts self-describing:

- include `lmdeploy.__file__`, branch, commit, Python, torch, Triton, CUDA, GPU,
  quant policy, dtype, shape, block size, split/warp/stage overrides, and correctness,
- write one JSONL row per case and keep metadata stable across runs,
- do not mix branches or checkout imports without explicit `PYTHONPATH`,
- mark concurrent same-GPU runs as noisy and rerun serially before accepting,
- keep benchmark-only force hooks out of production paths.

Use `scripts/summarize_kernel_bench.py` to inspect many artifacts quickly, then
rerun only the missing or noisy slices.

## Patch Selection

Use profiler evidence to choose the edit:

- `flatten_kv_cache` dominates: bypass, fuse, or change dataflow before tuning attention.
- paged decode first kernel dominates: tune tile shape, split-K, scale loads, or memory coalescing.
- reduce dominates: reduce split-K, fuse reduce only if correctness and scratch layout are simple.
- cache fill dominates: inspect vectorization, scale computation, metadata stores, and page/block indexing.
- CPU gaps or many tiny kernels dominate: consider dispatch consolidation or graph-capture compatibility.

Keep the first accepted patch small enough that one before/after table explains
why it is correct and faster.
