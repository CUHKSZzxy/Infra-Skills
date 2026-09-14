# LMDeploy CUDA Graph and MTP mapping

In a mixed target/draft capture, one kernel name can occur once in every target
layer and once in the recurrent MTP layer. Applying a layer count to the global
anchor list would then label draft work as target layers. Separate execution
phases before calling the annotation helper.

## Identify complete graphs

Match each `cudaGraphLaunch` to GPU kernels through `args.correlation`, scoped
to the selected rank/device. Use containing CPU `forward_cudagraph` and
`draft_model_forward` annotations on the launch's PID/TID to establish phase.
Check that the launch lies fully inside its scope. Kernel timestamps need not
lie inside the CPU scope: those scopes measure host submission.

Verify the target/draft ordering against the captured speculative settings.
Count anchors and an independent landmark separately within every graph being
labeled. Reject incomplete or inconsistent graphs. Do not hardcode a count of
draft passes, target layers, or CUDA streams from another capture.

## GLM-MoE-DSA example

In a verified six-target-layer TP4/DCP2 capture with one recurrent MTP layer:

- `GlmMoeDsaModel.forward` visits target layers in order.
- `GlmMoeDsaAttention.forward` calls the rotary-position operation once per
  layer. `apply_rotary_pos_emb_qk_kernel` was a suitable anchor in this build.
- Each target graph had six anchors and six each of
  `_filter_and_compact_dcp_indices_kernel` and
  `_correct_dcp_attention_output_kernel`; each draft graph had one of each.
- Each anchor interval had two BF16 TP all-reductions: attention output, then
  MLP output. Only the latter was selected as a terminal. A regex matching both
  reductions would be ambiguous.
- The MTP source started at `config.num_hidden_layers`, so its single layer
  was L6, reused for each draft step. Target guides were L0–L5.

Recheck these names, call sites, counts, and layer indices against the supplied
capture's source revision, saved dirty patch, and config hash. Fused kernels,
different topology, and other models can invalidate these landmarks.

## Use the helper without losing raw events

For phases sharing the same anchor name, select only that phase's verified
anchor and terminal events in a temporary in-memory event list. Call
`add_layer_track.annotate` on that list; append only its new guide and metadata
events to the complete original trace. Do not export the filtered selection
as though it were the complete trace.

When adding target and draft guides separately, allocate distinct unused guide
TIDs and update both event metadata and report IDs. Convert relative report
times to the full trace's origin; the filtered selection has a different
minimum timestamp. Preserve each phase's evidence and mapping report. Compact
the combined document once with `compact_gpu_tracks.compact`.

Optional phase spans run from the first to last GPU kernel of the correlated
graph. Label them as graph GPU spans: they include execution gaps and are not
host scopes or uninterrupted GPU busy time. A final layer guide ending at the
MLP reduction excludes subsequent model normalization. Neither type of guide
establishes exclusive kernel ownership or exact full-layer latency.

Validate exact reconstruction and Perfetto import as described in
[navigation.md](navigation.md). Keep adapted scripts and reports under the
run's `analysis/` directory and derived traces under `profiles/`, following
[artifact conventions](../../../docs/conventions/benchmark-artifacts.md).
