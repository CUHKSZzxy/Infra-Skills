---
name: triton-kernel-performance
description: Use when optimizing, reviewing, or validating LMDeploy PyTorch CUDA/Triton kernels for correctness and speed, especially attention, KV cache, quantization, FP8 KV cache, and Qwen3/Qwen3.5-family workloads.
---

# Triton Kernel Performance For LMDeploy

## Intent

Use this skill for kernel PRs where correctness and performance both matter. The goal is a reproducible loop:

1. identify the exact kernel path and shapes,
2. prove correctness against a reference,
3. benchmark the current code,
4. profile before changing heuristics,
5. patch one bottleneck at a time,
6. re-run the same correctness and performance gates.

Prefer this with `lmdeploy-attention-dataflow` and `check-env` when the
runtime path or repo/env is uncertain.

## Bundled Helpers

- `scripts/kernel_bench_utils.py`: import into ad hoc kernel microbenchmarks for CUDA-event timing, device metadata, correctness summaries, and JSONL rows.
- `scripts/kernel_microbench.py`: generic CUDA-event runner for small case files that define direct LMDeploy kernel calls.
- `scripts/microbench_case_template.py`: copyable case-file template for adding setup, run, and correctness hooks for a new kernel.
- `scripts/summarize_kernel_bench.py`: compact table view for one or more JSONL benchmark artifact files.
- `scripts/compare_kernel_bench.py`: compare baseline/candidate JSONL benchmark rows and fail on correctness failures or configurable regressions.
- `scripts/qwen_pytorch_smoke.py`: run a minimum Qwen3/Qwen3.5 PyTorch pipeline smoke with text and/or single-image prompts before and after kernel changes.
- `references/hopper-triton-heuristics.md`: load only for Hopper/H100/H800 tuning, Nsight metric selection, or SM90-specific heuristic questions.
- `references/lmdeploy-kernel-patterns.md`: load when optimizing LMDeploy attention/KV-cache pipelines, interpreting split-K sweeps, or deciding whether to fuse/bypass flatten/dequant work.

## 1. Scope The Kernel

Start from the runtime path, not from a full repo scan.

Common LMDeploy CUDA/Triton entry points:

- KV cache write: `lmdeploy/pytorch/kernels/cuda/fill_kv_cache.py`
- KV cache flatten/readback: `lmdeploy/pytorch/kernels/cuda/flatten_kv_cache.py`
- Decode attention: `lmdeploy/pytorch/kernels/cuda/pagedattention.py`
- Backend dispatch: `lmdeploy/pytorch/backends/cuda/attention/`
- Cache allocation and metadata: `lmdeploy/pytorch/engine/cache_engine.py`
- Quant policy plumbing: `lmdeploy/messages.py`, `lmdeploy/cli/utils.py`

For attention/KV-cache work, use `lmdeploy-attention-dataflow` first when the
runtime path is unclear. Performance conclusions are only meaningful after the
actual backend path is known.

Record the target:

- model/checkpoint, especially Qwen3/Qwen3.5 dense, MoE, GDN, or VL variant
- GPU type, CUDA, torch, triton, LMDeploy commit
- stage: prefill, decode, speculative decode, cache fill, flatten, sampling
- dtypes and quantization: BF16/FP16/FP8, KV cache quant policy, scale layout
- shapes: batch, seq lengths, block size, heads, kv heads, head dim, page/block counts

## 2. Correctness First

Do not tune a kernel whose semantics are still fuzzy.

- Compare against a simple PyTorch reference or existing unquantized path.
- Test non-contiguous strides if the public caller can produce them.
- Test boundary masks: partial last block, empty-ish sequences, uneven context lengths, and page table indirection.
- For quantized KV cache, verify scale direction explicitly: quantize as `fp_value / scale`, dequantize as `stored_value * scale`, and ensure every reader path receives the scale.
- Guard unsupported backends and fast paths. If a path cannot consume quant metadata, reject it near dispatch instead of letting it run silently.
- Keep K and V dimensions separate unless the model contract proves they are identical.
- Separate semantic dtype from physical storage. A tensor stored as `torch.float8_*`, a packed `uint8` payload, and a custom bit layout need different cache descriptors, kernel casts, test references, and tolerances.
- Check GPU capability before adding or trusting a Triton conversion path. Some dtype conversions compile on one architecture and fail on another; skip or route only the unsupported slice, not the whole feature, when possible.
- Compare quantized outputs in the domain that proves the contract. Raw payload equality is useful for deterministic encoders; dequantized-value comparison is often the better assertion for approximate formats.

For FP8 KV cache, pay special attention to:

- `torch.float8_e4m3fn` range and saturation behavior,
- per-token/per-head scale shape and stride,
- scale metadata lifetime through fill, flatten, decode, and speculative decode,
- accuracy tolerances against the no-quant baseline,
- Qwen3.5-style FP8/KV-scale naming or remapping issues when loading model-side scales.

## 3. Baseline Performance

Capture a baseline before editing.

Minimum artifact notes:

```text
repo:
commit:
branch:
python:
torch/triton/cuda:
gpu:
model:
command:
workload:
metric before:
```

Use two lanes when possible:

- Microbench: direct kernel benchmark with CUDA events, warmup, enough iterations, fixed random seed, and correctness check.
- Macrobench: real `lmdeploy` pipeline or serve workload with fixed prompts, max tokens, concurrency/request rate, quant policy, and backend flags.

When benchmarking multiple branches/worktrees with an editable env, pin the
imported checkout explicitly:

```bash
CUDA_VISIBLE_DEVICES=X PYTHONPATH=/path/to/lmdeploy-checkout \
  /path/to/feature-env/bin/python bench.py
```

Check the benchmark metadata includes `lmdeploy.__file__`; otherwise a main
worktree benchmark can accidentally import the feature branch from the env.

For a new direct-kernel microbench, start from the generic runner instead of
rewriting the timing loop. Copy `scripts/microbench_case_template.py`, replace
its setup/run/check functions with the target kernel call, then run:

```bash
CUDA_VISIBLE_DEVICES=X PYTHONPATH=/path/to/lmdeploy-checkout \
  /path/to/lmdeploy-env/bin/python \
  /nvme1/zhouxinyu/LMDeploy-Skills/skills/triton-kernel-performance/scripts/kernel_microbench.py \
  path/to/my_case.py --out artifacts/candidate.jsonl --label candidate --warmup 25 --repeat 100 \
  -- --case-specific-arg value
```

Use the lower-level helper only when the generic case-file interface is too
restrictive:

```python
from scripts.kernel_bench_utils import append_jsonl, cuda_event_bench, summarize_times
```

Then compare candidates:

```bash
python /nvme1/zhouxinyu/LMDeploy-Skills/skills/triton-kernel-performance/scripts/compare_kernel_bench.py \
  artifacts/baseline.jsonl artifacts/candidate.jsonl
```

For a fast read of many artifact files, summarize them before deciding what to
rerun:

```bash
python /nvme1/zhouxinyu/LMDeploy-Skills/skills/triton-kernel-performance/scripts/summarize_kernel_bench.py \
  benchmark/artifacts/*.jsonl
```

Never compare a tuned candidate against a stale or differently configured baseline.

Before/after kernel work, a quick end-to-end smoke can catch dispatch, quant-policy, and multimodal regressions that microbenches miss:

```bash
CUDA_VISIBLE_DEVICES=X /path/to/lmdeploy-env/bin/python \
  /nvme1/zhouxinyu/LMDeploy-Skills/skills/triton-kernel-performance/scripts/qwen_pytorch_smoke.py \
  --model /path/to/Qwen-or-Qwen3.5-checkpoint --case all --tp 1
```

Use an environment whose `lmdeploy` import points at the checkout being optimized. Use `--case text` for text-only checkpoints and `--case all` for multimodal checkpoints.

## 4. Profile Before Patching

Use profiler evidence to choose the edit.

Look for:

- kernel wall time and invocation count,
- memory bandwidth vs compute saturation,
- occupancy, register pressure, spills, shared-memory pressure,
- excessive tiny kernels around the hot path,
- hidden synchronizations, host/device copies, or shape-dependent recompilation,
- missed fusion or overlap opportunities around RoPE, norm, cache write, and attention.

For LMDeploy attention/KV-cache optimization, profile stages independently:
cache fill, decode attention, flatten/readback, prefill attention, and pipeline
smoke. A full pipeline number alone can hide whether the bottleneck is in cache
write, flatten/dequant, paged attention, or launch/reduce overhead.

When comparing branches or policy variants, keep the matrix explicit:

- baseline branch and candidate branch,
- public policy/config value,
- cache payload dtype and metadata allocation,
- active attention backend,
- GPU architecture,
- exact shape family.

If one row changes both semantics and performance behavior, split it into a
smaller comparison before drawing conclusions.

When using torch profiler, report the same three views:

- kernel table: top CUDA/Triton kernels by GPU time,
- overlap-opportunity table: idle windows, collectives, CPU gaps, stream gaps,
- fuse-pattern table: adjacent kernels that may safely become one path.

For Qwen3/Qwen3.5-family work, check whether existing optimized-family ideas apply before inventing a new one:

- split Q/K norm placement,
- RoPE plus cache-write fusion,
- projection or GDN fusion,
- alt-stream overlap,
- FP8 scale handling and remapping,
- MTP/speculative decode compatibility.

For Hopper/H100/H800, load `references/hopper-triton-heuristics.md` before choosing Nsight metrics or changing Triton block/warp/stage heuristics.

## 5. Triton Heuristics

Tune only dimensions that are connected to the measured bottleneck.

Memory/layout:

- Make the fastest-moving dimension the vectorized load/store dimension.
- Keep loads coalesced across lanes; avoid gathering when a layout change or index transform can make it contiguous.
- Hoist stride and offset math outside repeated inner expressions when possible.
- Use masks only where needed, and keep mask predicates simple.
- Avoid extra reads/writes of scale or metadata inside element loops.

Compile-time specialization:

- Use `tl.constexpr` for branchy feature flags, head dim, group size, block size, and quant mode.
- Prefer separate specializations for genuinely different layouts or dtypes over one heavily branched kernel.
- Keep autotune candidate lists small and shape-relevant; large autotune grids can hurt usability.

Block and warp choices:

- Start around the real model shapes: head dim 64/128/256, block size 16/32, typical Qwen KV heads.
- Favor powers of two for block dimensions used by `tl.arange`.
- Increase `num_warps` only when the tile has enough work; watch register pressure and occupancy.
- Adjust `num_stages` based on memory latency hiding, not as a ritual.
- Measure small-batch decode and large-prefill separately; one heuristic rarely wins both.

Split-K / parallelism:

- Sweep split-K or equivalent parallelism only after the decode kernel is the measured bottleneck.
- Label forced heuristic runs in benchmark metadata; unlabeled split sweeps are not trustworthy evidence.
- Check short and long contexts. More split parallelism can help long-context decode while doing nothing or hurting short context.
- Watch the reduce kernel. If the first split kernel improves but reduce time grows enough to erase the win, stop increasing split-K.
- Guard production heuristic changes by quant policy, hardware capability, and shape whenever the data only covers that slice.

Numerics and quantization:

- Accumulate in the intended dtype; do not accidentally force FP32 in a bandwidth-bound path.
- For FP8, keep scale loads in FP32/BF16 as required by the math and cast explicitly near use.
- Validate saturation and zero-scale protection on random, near-zero, and large-amplitude inputs.

## 6. Patch Discipline

Patch narrowly:

- one kernel or dispatch choice at a time,
- no unrelated formatting,
- no benchmark-only behavior changes,
- clear guards for hardware, dtype, backend, and unsupported model shapes.

If a kernel has both correctness and speed issues, fix correctness first, then tune speed in a separate step when practical.

## 7. Validation Contract

Before calling a kernel optimization done, provide:

- changed files,
- correctness tests or reference comparisons and tolerances,
- exact benchmark commands,
- before/after table for latency, throughput, or kernel time,
- profiler evidence if the claimed win is kernel-level,
- residual risks such as untested GPU, unsupported FA/speculative path, or missing macrobench.

Treat concurrent runs on the same GPU as suspect unless isolation is proven.
Rerun the winning and baseline candidates serially on an idle GPU before
claiming a speedup.

Recommended final table:

| Lane | Baseline | Candidate | Delta | Notes |
| --- | ---: | ---: | ---: | --- |
| micro kernel time | | | | |
| pipeline/serve throughput | | | | |
| accuracy/correctness | | | | |

Do not claim a speedup from a single noisy run. For small deltas, rerun enough samples to decide whether the change is real; treat under 3-5% as noise unless variance is measured lower.
