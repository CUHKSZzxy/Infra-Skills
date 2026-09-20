---
name: support-new-model
description: Use when adding or reviewing an LLM or VLM architecture in LMDeploy's PyTorch backend.
---

# LMDeploy Model Support

Match the checkpoint contract: exact architecture/model type, dimensions,
RoPE/MoE/recurrent/MTP configuration, and modality token/length semantics.
Use nearby working LMDeploy implementations. HF is the reference for model
behavior; consult another runtime when it resolves a specific porting ambiguity.

## Registration And Runtime Contracts

- PyTorch support normally needs `models/<model>.py` and `models/module_map.py`
  under `lmdeploy/pytorch/`. Add a configuration builder for nonstandard or
  nested configs, not as boilerplate.
- Keep packed parameter names, shard IDs, and `load_weights()` aligned with the
  checkpoint. Verify weight loading and inference behavior, including prefill
  and decode for recurrent/MTP paths.
- Use LMDeploy inference primitives when parameter loading, layout, masks, and
  backend metadata match the reference. Similar math alone does not establish
  that an auxiliary encoder or projector can use the same operator.
- VLM support also uses `lmdeploy/vl/model/<model>.py`, its builder import, and
  `lmdeploy/archs.py`. Prefer the current `MultimodalSpecialTokens` /
  `VisionModel.get_input_prompt(...)` / `preprocess(...)` path.
- Preserve modality-specific placeholder expansion, feature lengths, and
  position metadata. Related image/video/audio families can differ here.

## References By Need

| Question | Reference |
| --- | --- |
| Which nearby implementation or registry? | [Key files](references/key-files.md) |
| How do HF ops map to LMDeploy? | [HF porting](references/hf-to-lmdeploy-porting.md) |
| Which recent support pattern fits? | [Recent patterns](references/recent-pytorch-model-support-patterns.md) |
| Dense model/config implementation? | [LLM shape](references/llm-porting-shape.md) |
| New auxiliary encoder or modality? | [Side encoders](references/side-encoder-porting.md) |
| VLM preprocessing? | [Preprocessor](references/vlm-preprocessor.md) |
| Output differs from the reference? | [Parity triage](references/parity-triage.md) |
| Known registration, token, or loader failure? | [Pitfalls](references/pitfalls.md) |

## Completion

For implementation, verify generation/parity for the new architecture and
modalities. After an op replacement or simplification that changes computation,
rerun affected numeric parity. For shared modules, check the existing supported
model as well. Choose relevant tests and small pipeline requests; broad VL
suites are conditional on shared impact. Keep public tests portable if local
cached media/checkpoints were used for validation, and report unavailable
parity evidence.

For review, assess the affected contracts and supplied evidence; run additional
checks when needed to resolve a concrete finding.
