# Side Encoder And New-Modality Porting

Load this only when a model adds a nonstandard modality or auxiliary encoder,
such as time series or scientific signals. Keep transport, preprocessing,
embedding, and language-model scatter as separate contracts.

## Modality Contract

- Read the side-module config first: token ids, input feature dimensions,
  downsampling strides, projector size, and sampling-dependent formulas.
- Add a new modality consistently to `Modality`,
  `VisionModel.ATTR_NAME_TO_MODALITY`, `VisionModel.FEATURE_NAMES`,
  `MultimodalSpecialTokens`, the serve parser, and PyTorch `MultiModalData`
  conversion.
- Preserve the reference token-count formula exactly. Placeholder count must
  equal the number of embeddings scattered into the language model.
- Decide explicitly whether the modality participates in M-RoPE. Do not inherit
  image/video position behavior without checking the reference model.

## Encoder Port

- Build a reusable side encoder as a separate module. Keep checkpoint parameter
  names aligned with the real state dict.
- Use LMDeploy linear and norm helpers for checkpointed projections when they
  preserve the contract. Keep simple compatible operations such as `Conv1d`,
  positional buffers, or local reference blocks when no runtime replacement
  exists.
- Port inference behavior only. Drop training-only dropout, freeze switches,
  output flags, and dead modes unless the runtime consumes them.
- Pass `dtype` and `device` explicitly, following nearby model files. Do not add
  local factory abstractions without an established local pattern.
- If full integration or weights are unavailable, first validate the standalone
  encoder against the reference. Report shape equality and max absolute error;
  treat relative error near zero-valued outputs as secondary.

## Runtime Integration

```text
raw payload
  -> media IO
  -> modality preprocessing + placeholder expansion
  -> MultiModalData(features, token range, metadata)
  -> side encoder
  -> masked scatter into inputs_embeds
  -> language model
```

- In `prepare_inputs_for_generation`, collect side-modality data, concatenate
  feature tensors and required metadata, and build the token mask.
- In model `forward`, run the side encoder only when side inputs are present,
  then scatter embeddings before calling the language model.
- Store the original nested HF config on `cfg.hf_config` when runtime code still
  needs non-text configuration after deriving text-engine fields.

## Verification

- Check placeholder count against side-encoder output length before generation.
- Verify preprocessing metadata, each checkpointed submodule, end-to-end encoder
  output, and final masked scatter.
- Run one normal text/image regression when the new wrapper reuses an existing
  public multimodal model.
