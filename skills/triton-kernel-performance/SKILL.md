---
name: triton-kernel-performance
description: Use when an LMDeploy CUDA/Triton kernel change needs correctness or performance validation, especially attention, KV cache, quantization, FP8 KV cache, or Qwen-family workloads.
---

# Triton Kernel Performance For LMDeploy

Use this for kernel work where correctness and speed both matter. Do not use it
for ordinary model wiring or serving bugs unless the failing boundary is already
a CUDA/Triton kernel.

Pair with:

- `lmdeploy-attention-dataflow` when the active attention/KV path is uncertain.
- `check-env` when Python, CUDA, GPU visibility, or import path is uncertain.

## 1. Scope First

Record the exact target before editing:

- kernel or dispatch path,
- model/checkpoint and stage: prefill, decode, cache fill, flatten, sampling,
- GPU, CUDA, torch, triton, LMDeploy commit,
- dtype and quant policy,
- shape family: batch, seqlen, block size, heads, kv heads, head dim.

Common anchors:

- KV cache write: `lmdeploy/pytorch/kernels/cuda/fill_kv_cache.py`
- KV cache flatten/readback: `lmdeploy/pytorch/kernels/cuda/flatten_kv_cache.py`
- Decode attention: `lmdeploy/pytorch/kernels/cuda/pagedattention.py`
- Attention dispatch: `lmdeploy/pytorch/backends/cuda/attention/`
- Cache metadata: `lmdeploy/pytorch/engine/cache_engine.py`

## 2. Correctness Before Speed

Do not tune unclear semantics.

- Compare against a simple PyTorch reference or existing unquantized path.
- Test boundary shapes: partial blocks, uneven context lengths, empty-ish inputs,
  page table indirection, and non-contiguous strides if callers can produce them.
- For quantized KV cache, verify both payload and metadata. Unsupported readers
  must be rejected near dispatch, not allowed to run silently.
- Keep K and V dimensions separate unless the model contract proves otherwise.
- For FP8, check saturation/range behavior, scale shape and lifetime, and
  dequantized-value tolerances against the no-quant baseline.

## 3. Benchmark With Metadata

Capture a baseline before editing. Minimum artifact:

```text
repo/commit/branch:
python/torch/triton/cuda:
gpu:
model:
command:
workload:
metric before:
```

Use the bundled helpers instead of rewriting timing loops:

- `scripts/kernel_microbench.py`: generic CUDA-event microbench runner.
- `scripts/microbench_case_template.py`: copyable case-file template.
- `scripts/summarize_kernel_bench.py`: table view for JSONL artifacts.
- `scripts/compare_kernel_bench.py`: baseline/candidate comparison.
- `scripts/qwen_pytorch_smoke.py`: small Qwen pipeline smoke.

Pin the imported checkout when comparing branches:

```bash
CUDA_VISIBLE_DEVICES=X PYTHONPATH=/path/to/lmdeploy-checkout \
  /path/to/env/bin/python bench.py
```

Check benchmark output includes `lmdeploy.__file__`; otherwise the wrong
checkout may be imported.

## 4. Patch Narrowly

Change one kernel, dispatch choice, or heuristic at a time. Keep guards explicit
for hardware, dtype, backend, quant policy, and unsupported model shapes.

Profile before changing heuristics. Useful references:

- `references/hopper-triton-heuristics.md`: H100/H800/SM90 tuning and Nsight.
- `references/lmdeploy-kernel-patterns.md`: attention/KV-cache optimization
  patterns such as split-K, flatten/dequant bypass, and fusion choices.

Treat concurrent GPU runs as suspect. Rerun baseline and candidate serially on
an idle GPU before claiming a speedup. Treat small deltas under about 3-5% as
noise unless variance is measured lower.

## 5. Report Contract

Before calling the work done, report:

- changed files,
- correctness command and tolerance,
- benchmark command,
- before/after table,
- profiler evidence if claiming a kernel-level win,
- residual risk: untested GPU, backend, FA/speculative path, or macrobench.
