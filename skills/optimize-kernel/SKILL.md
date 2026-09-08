---
name: optimize-kernel
description: Use when optimizing or validating an identified LMDeploy CUDA/Triton kernel or dispatch path.
---

# LMDeploy Kernel Optimization

Work from the identified kernel and production shapes. Use
`lmdeploy-attention-dataflow` if attention/KV dispatch is unclear, or
`profile-serving-timeline` if the bottleneck has not been localized.

## Correctness And Timing

Apply correctness checks to validation requests and timing contracts to
performance comparisons. Campaigns serve iterative optimization requests.

- Compare equivalent baseline/candidate inputs and callable boundaries against
  an existing reference. Index/layout transformations require exact agreement;
  choose floating-point tolerances for the dtype and changed arithmetic.
- Exercise reachable boundary shapes, strides, fallback dispatch, and graph/eager
  modes affected by the edit. KV quantization includes payload and scale/zero
  metadata; preserve independent K/V dimensions, FP8 range, and scale lifetime.
- Use a model accuracy check when changed arithmetic can affect output. It
  supplements focused kernel checks; it does not replace them.
- Record source revision/import path, Python/torch/Triton/CUDA, GPU, dtype,
  quant policy, shape, command, warmup, repetitions, and statistics. Preserve a
  baseline that can be rerun after editing.
- Warm JIT, allocations, and graph capture. Interleave A/B samples on the same
  idle GPU using CUDA events or synchronized timing. Compare representative
  and boundary shapes, report spread and regressions, and rerun contaminated
  or inconclusive cases. Deltas below roughly 3-5% need measured low variance.

## Tools And References

Use bundled runners for consistent timing:

- `scripts/kernel_microbench.py` and `scripts/microbench_case_template.py` for
  one-off or paired cases;
- [bounded campaigns](references/bounded-campaign.md) for multiple hypotheses
  with frozen workloads and resumable evidence;
- `scripts/summarize_kernel_bench.py` for result tables and
  `scripts/compare_kernel_bench.py` for separate legacy artifacts;
- `scripts/qwen_pytorch_smoke.py` when a Qwen pipeline check fits the change.

Use [LMDeploy patterns](references/lmdeploy-kernel-patterns.md) for attention/KV
anchors and split-K or fusion decisions. Use
[external kernel evidence](references/external-kernel-evidence.md) for
architecture-specific KernelWiki references or NCU counters when timing leaves
a bottleneck unexplained. Neither external lookup nor profiling is a
prerequisite for every edit.

## Completion And Claims

Continue within the requested scope or campaign budget while useful hypotheses
remain. Resolve correctness failures before accepting a speedup; inconclusive
results are not a win.

Paired timing supports the measured kernel/shape/hardware result. Establish the
executed path with dispatch checks or a trace when uncertain. Claims about
launches, copies, or synchronization need corresponding evidence; serving-level
claims need a separate `benchmark-efficiency` run.

Report the requested correctness or timing evidence, commands, and relevant
gaps. For a performance comparison, include before/after results with spread
and shape coverage. Include NCU report paths and KernelWiki source IDs when used.
