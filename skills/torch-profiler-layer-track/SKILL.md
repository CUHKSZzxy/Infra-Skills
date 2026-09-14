---
name: torch-profiler-layer-track
description: Use when adding verified layer guides or compact GPU display lanes to an existing Torch Profiler trace.
---

# Torch Profiler Layer Track

Create a separate Chrome JSON trace with verified `L0, L1, ...` guides and
optional compact GPU display lanes. Preserve the source file, recorded timing,
kernel names, real stream IDs, and CPU events. Synthetic lanes change the
visualization, not execution or CUDA stream scheduling.

Adapted from [BBuf/AI-Infra-Auto-Driven-SKILLS](https://github.com/BBuf/AI-Infra-Auto-Driven-SKILLS/tree/b84a62a6eb4f341cf9449c2e4c202f5ebb694946/skills/torch-profiler-layer-track).
Use `profile-serving-timeline` for new captures or bottleneck analysis.

## Establish the mapping

Obtain the layer count and order from the matching config/source revision.
Identify the rank/GPU, execution phase, and one complete forward pass. Separate
target verification from speculative draft passes; batch size does not identify
the number of tokens being verified.

Choose a kernel that runs exactly once per layer in that phase. Verify its call
site and cross-check another landmark or module scopes across all GPU streams.
Locate the first L0 explicitly: divisibility alone cannot exclude a partial
first pass or mixed draft/target anchors. If the evidence is insufficient,
report the ambiguity instead of adding confident labels.

For LMDeploy CUDA Graph/MTP traces, read
[LMDeploy phase mapping](references/lmdeploy.md). For other builds and detailed
Perfetto checks, use [navigation and evidence](references/navigation.md).

## Generate the view

Scripts require Python 3.10+ and the standard library. Commands below are
relative to this skill directory:

```bash
python3 scripts/add_layer_track.py \
  --trace /path/to/rank0.json.gz \
  --output /path/to/rank0.layers.json.gz \
  --anchor-regex '^VERIFIED_ONCE_PER_LAYER_KERNEL$' \
  --num-layers 6 --anchor-offset 0 --passes 2 \
  --max-gpu-lanes 10 --phase target-verify \
  --evidence 'Matching config/source revision; verified first L0 and anchors per pass; draft excluded.'
```

Replace the example layer count and selection with verified values. Select
`--pid` and `--device` when necessary; `--first-layer` supports a known pipeline
partition. `--passes` labels only complete passes. An optional
`--end-anchor-regex` must identify exactly one terminal kernel between anchors.
Without it, the final layer is a zero-duration marker, never extended into the
next draft pass or iteration.

The command writes a new `.json` or `.json.gz` trace and an adjacent
`.layers.json` mapping report. Omit `--max-gpu-lanes` to preserve stream layout.
For an already verified annotated trace, `scripts/compact_gpu_tracks.py`
accepts `--trace`, `--output`, and `--max-gpu-lanes 10` without adding guides.

Compaction preserves concurrent activity and remaps GPU flow endpoints. It
rejects ambiguous events or more than ten overlapping lanes. Original GPU
placement remains in `args._compact_gpu_track`; retired metadata is in the
report. GPU user annotations move to a separate `GPU scopes` process. Keep
large traces and private capture paths out of public skill/PR artifacts.

## Verify and deliver

Check the report's phase, rank, layer count, offset, and source hash. Check at
least two passes before claiming that numbering repeats across iterations.
Without compaction, original events must remain an unchanged prefix. With it,
reverse placement changes and restore retired metadata to reconstruct that
prefix exactly; also verify top-level metadata and the source-file hash.

Open the output in Perfetto with **Open trace file**. Confirm original kernel
counts and actual imported tracks: each activity lane and guide should have
depth zero. Pin `Layer guide (...) — anchor intervals` beside the GPU lanes.
For loopback viewing, `scripts/serve_local_trace.py --trace PATH` serves only
that file and its viewer; the browser needs access to the Perfetto UI. When
working remotely, the browser must be able to reach that loopback endpoint,
otherwise open a local copy manually.

Return the trace and report, original stream count and synthetic lane count,
and relevant relative timestamps. If a screenshot is requested, capture the
actual viewer. State any unavailable import or visual inspection. Numbering is
zero-based; guides run from one anchor to the next, not across exact full-layer
boundaries or exclusive kernel ownership. Preserve this limitation in reports.
