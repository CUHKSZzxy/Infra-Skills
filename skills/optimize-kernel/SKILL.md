---
name: optimize-kernel
description: Use when optimizing or validating an identified LMDeploy CUDA/Triton kernel or GPU dispatch path with correctness, timing, KernelWiki, or Nsight Compute evidence; do not use for unresolved serving or model-wiring bugs.
---

# Optimize Kernel For LMDeploy

Pair with:

- `lmdeploy-attention-dataflow` when the active attention/KV path is uncertain.
- `check-env` when Python, CUDA, GPU visibility, or import path is uncertain.
- `profile-serving-timeline` when the kernel hotspot is not yet proven.
- `benchmark-efficiency` when the claim extends to serving performance.

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
- Use exact equality for indexing, copies, and layout transforms. For floating
  point outputs, state why the chosen `atol` and `rtol` fit the dtype and math.
- Test boundary shapes: partial blocks, uneven context lengths, empty-ish inputs,
  page table indirection, and non-contiguous strides if callers can produce them.
- Test dispatch selection and the unsupported-hardware fallback. Cover eager and
  CUDA Graph execution when the changed path supports both.
- For quantized KV cache, verify both payload and metadata. Unsupported readers
  must be rejected near dispatch, not allowed to run silently.
- Keep K and V dimensions separate unless the model contract proves otherwise.
- For FP8, check saturation/range behavior, scale shape and lifetime, and
  dequantized-value tolerances against the no-quant baseline.
- Run a model-level accuracy check only when changed arithmetic can affect model
  output; it does not replace focused kernel correctness tests.

## 3. Benchmark With Metadata

Capture a baseline before editing. Minimum artifact:

```text
repo/commit/branch:
python/torch/triton/cuda:
gpu:
model:
command:
workload/shape sweep:
warmup/repetitions/statistic:
metric before/after:
```

Use the bundled helpers instead of rewriting timing loops:

- `scripts/kernel_campaign.py`: bounded, resumable paired benchmark campaign.
- `scripts/kernel_microbench.py`: paired or single-case CUDA-event runner.
- `scripts/microbench_case_template.py`: copyable paired-case template.
- `scripts/summarize_kernel_bench.py`: table view for JSONL artifacts.
- `scripts/compare_kernel_bench.py`: comparison for separate legacy artifacts.
- `scripts/qwen_pytorch_smoke.py`: small Qwen pipeline quick check.
- `references/external-kernel-evidence.md`: KernelWiki lookup and optional NCU
  collection, analysis, and report workflow.

Pin the imported checkout when comparing branches:

```bash
CUDA_VISIBLE_DEVICES=X PYTHONPATH=/path/to/lmdeploy-checkout \
  /path/to/env/bin/python bench.py
```

Check benchmark output includes `lmdeploy.__file__`; otherwise the wrong
checkout may be imported.

Warm JIT compilation, allocations, and graph capture before timing. Use CUDA
events or the helper's synchronized timing. Interleave baseline and candidate
samples on the same idle GPU, and report median plus spread or quantiles. Sweep
representative prefill/decode shapes and include neutral or regressing cases.

## 4. Run A Bounded Campaign

Use a campaign for multiple optimization hypotheses and the single runner for
one-off validation. Start from `scripts/microbench_case_template.py`; each
`BenchmarkPair` must compare equivalent baseline/candidate callables for one
production-relevant shape and record tolerances plus path-affecting knobs.

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/local-conventions.md}"
: "${CONDA_ROOT:?set CONDA_ROOT from docs/local-conventions.md}"
: "${LMDEPLOY_DEV_SOURCE:?set LMDEPLOY_DEV_SOURCE from docs/local-conventions.md}"
SKILL_DIR="$INFRA_SKILLS_HOME/skills/optimize-kernel"
PYTHON_BIN="$CONDA_ROOT/envs/dev/bin/python"
RUN_DATE=${RUN_DATE:-$(date +%Y%m%d)}
RUN_DIR="$LMDEPLOY_DEV_SOURCE/benchmark/${RUN_DATE}_kernel_<target>"

"$PYTHON_BIN" \
  "$SKILL_DIR/scripts/kernel_campaign.py" init "$RUN_DIR" \
  --case-file /path/to/kernel_cases.py \
  --source-checkout "$LMDEPLOY_DEV_SOURCE" \
  --python "$PYTHON_BIN" \
  --gpu 0 --max-rounds 5

"$PYTHON_BIN" \
  "$SKILL_DIR/scripts/kernel_campaign.py" run "$RUN_DIR" \
  --hypothesis "Coalesce cache payload loads for long decode contexts"
```

Initialization freezes the case-file hash; the first run freezes
`workloads.json`. Create a new campaign when shapes, tolerances, required
cases, or headline cases change. Each round records the hypothesis, command,
samples, decision, and comparison report; `status` reports the checkpoint.

For each round, make one narrow edit, run focused correctness before timing,
let the paired runner interleave A/B samples, and keep a candidate only after
dispatch and integration validation. Stop on unclear correctness, changed
scope, inconclusive evidence, or the configured budget. The wrapper defaults to
one GPU, checkpoints evidence, and does not edit, commit, or push source. Use
NCU or a serving trace only when it would choose the next edit.

When a hardware-specific technique or bottleneck is unclear, read
`references/external-kernel-evidence.md`. Query the pinned KernelWiki before
inventing a new design. Collect an NCU report only for a representative frozen
case and only after normal correctness and timing are stable. NCU explains why
a kernel behaves as measured; it does not replace paired timing or end-to-end
validation.

## 5. Patch Narrowly

Change one kernel, dispatch choice, or heuristic at a time. Keep guards explicit
for hardware, dtype, backend, quant policy, and unsupported model shapes.

Profile before changing heuristics. Useful references:

- `references/lmdeploy-kernel-patterns.md`: attention/KV-cache optimization
  patterns such as split-K, flatten/dequant bypass, and fusion choices.
- [KernelWiki](https://github.com/mit-han-lab/KernelWiki): external GPU kernel
  optimization references and examples; prefer the pinned local submodule.

Treat concurrent GPU runs as suspect. Rerun baseline and candidate in one
exclusive paired A/B session on an idle GPU before claiming a speedup. Treat
small deltas under about 3-5% as noise unless variance is measured lower.

Match the claim to the evidence:

- A microbenchmark supports only a kernel-level speed claim.
- Use a short profile to prove the intended kernel, copy, launch, or
  synchronization changed.
- Add an end-to-end benchmark when claiming throughput, TTFT, TPOT/ITL, memory
  capacity, or serving latency. A faster kernel need not improve serving.
- Do not claim a universal win from one GPU or one favorable shape. State the
  hardware and operating envelope where the change helps.

## 6. Report Contract

Before calling the work done, report:

- changed files,
- correctness command and tolerance,
- benchmark command,
- before/after table with shape coverage and observed spread,
- KernelWiki page IDs and NCU `REPORT.md` path with cited metrics when used,
- profiler evidence if claiming a kernel-level win,
- end-to-end evidence for serving-level claims,
- residual risk: untested GPU, backend, fallback, graph mode, FA/speculative
  path, or macrobench.
